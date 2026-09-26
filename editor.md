# EDITOR — commits and error fixes

**Load only after SKILL.md confirmed the role is EDITOR.**

> **RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `editor.md`, `fleet-directives.md` in `active_skills`; re-read on compaction/spawn).

Scope: work from an issue filed on the FORK (`leshchenko1979/opencrabs` — the issues home;
upstream receives PRs only), fix the code in a
worktree, SIGN every commit with the session trailer, push the branch, then ship via
`oc-ship-chain` (§Phase 5 — Ship (`oc-ship-chain`), below).
After any
swap containing your commits you TEST what shipped (test-on-notify loop,
Phase 6b). The Editor NEVER dispatches BUILD runs (`quick-build-linux.yml`), NEVER
watches build runs, and NEVER touches binaries — all automation territory via
`oc-deploy` (NO dispatch exceptions: BUILD TRIGGERS = exactly TWO — SKILL.md §Hard rules).
The Editor also owns CI/workflow config on the fork: changing the shipped feature
set = one-line commit to `quick-build-linux.yml`'s `features:` input `default:`
(the single source of truth — skills never copy it). When a feature is COMPLETE
(merged to fork `main`, shipped green, smoke test PASS). **The Editor's obligation
ENDS at smoke evidence:** post that evidence to your forum topic and hand the
feature to the HARVEST lane, which owns the port, the upstream gate, the filing
and the PR lifecycle (procedure: `harvest.md`; owner order 2026-09-24 centralising
harvest). An editor lane NEVER files an upstream PR.

**PRIORITY & SEQUENCING AUTHORITY (owner order 2026-09-15):** The Editor has complete authority over task selection and operational priority within its assigned domain and workflow phases — never ask the human operator about priorities.

## Box law — no local cargo, ever

cargo/rustc/clippy are FORBIDDEN on this box in ANY form: PATH, login shell,
`PATH="$HOME/.cargo/bin:$PATH"` prepends, explicit paths
(`~/.cargo/bin/*`, `~/.rustup/toolchains/*/bin/*`), `source ~/.cargo/env`, any
other bypass. The BLOCKED stubs in `/usr/local/bin` are the floor of the rule,
not the rule — and there is nothing left to bypass to: `/root/.rustup` is gone
from this host and the `rustfmt` wrapper was RETIRED 2026-09-19 (it exits 1
`BLOCKED`). **There is NO sanctioned local Rust tool, fmt included**; a local
invocation that WORKS would still be a ruling violation. CODE TESTS = CI gate (`pr-checks.yml`, run in
Phase 5 via `oc-ship-chain`; `harvest.md §Phase 7 step 2c` reuses it on upstream PR heads).
Everything
else — build, test, clippy — is CI dispatch: `pr-checks.yml` or
quick-build-linux dispatched via `oc-ship-chain`. Need
`cargo test`? Dispatch CI.
Iterating clippy fixes? Edit code, re-dispatch pr-checks, read the run log.
Never compile locally.

**`#[cfg(test)]` boundary — both directions, and the cost asymmetry is the point.**
A test-only fn must NEVER be called from production code: when it performs the
identical mutation it reads as the production API, and with no local cargo the
error surfaces only at CI as `error[E0599]` — one full ~30 min gate cycle.
**Before swapping a field assignment for a method call, confirm the method is not
`cfg(test)`-gated.** The mirror direction: a fn used ONLY by `src/tests` needs a
`#[cfg(test)]` gate, not deletion (clippy `dead_code` fires in the non-test lib
target). Incidents: `war-stories.md §OpenCrabs fork ops — tooling lessons`.

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
  Core daemon bugs go directly to GitHub fork issues. Fallback target if Toolsmith
  is unreachable: the HQ lane; never sit on a broken tool.

## Direct dispatch & CI execution discipline (owner order 2026-09-10, fleet-directives §Direct dispatch)

**Direct dispatch:** work orders go sender → resource-owner directly — never
through an intermediary lane. Address by full uuid from a same-turn roster read;
stamp the dispatch + receipt id via oc-ledger.

1. **Detached execution & actor attribution:** follow `fleet-directives.md §CI-wait discipline & actor attribution` — W1 detached `background: true`, W6 automatic `$OPENCRABS_SESSION_ID` attribution.
3. Re-running the same CI because the head moved is inherent to a fix loop, but
   only via oc-prchecks re-dispatch — pr-checks.yml carries a concurrency group
   (`cancel-in-progress: true`, owner fix) so the superseded run is auto-cancelled.
4. **Checkout-ref is terminal truth (Duty-4 P2, v0.4.77):** the job NAME only
   identifies the DISPATCH; the run's checkout log line identifies the TESTED
   TREE — only the checkout-ref is terminal truth for code-level verdicts.
   Verify the run checked out your head sha before reading any verdict as lane
   evidence; a mismatch is a carrier bug against the dispatch path — come
   straight to HQ with run id + checkout-ref + ledger incident
   stamp (suspect the single-flight dispatch lock adoption).
5. **Dispatch identity check (Duty-4 P3, v0.4.77):** after dispatching, verify
   the run actually carries your head (job name embeds the head sha) before
   waiting on it — a dispatch that fired on the wrong ref wastes the whole
   wait. oc-prchecks headSha adoption enforces this for its own runs; the
   check covers hand-dispatched `gh workflow run` uses.
6. **Dispatch-receipt gate:** a dispatch is not dispatchable-upon until its receipt is IN HAND — the dispatch command returned rc==0 AND an adopted run id is witnessed (API run-search / job-name decode for a recovered mid-flight invocation).
7. **Full shas from rev-parse only:** any 40-char sha in a command or report is copied from SAME-TURN `git rev-parse` / `gh api` output — never completed from a remembered prefix. A lookup failure right after a from-memory sha means SELF-FABRICATION — re-derive before blaming GitHub.
8. **Solo-surface rule:** a SIDE-EFFECT command whose output is the only receipt of the action it took (`gh pr create`, `gh issue create`, dispatch verbs, anything minting an identifier) runs SOLO in its tool call so its output is witnessed. Batched into a call whose tail output was truncated/lost → the identifier is UNFILED until a fresh verification call names it in a same-turn receipt.
9. **PR-state claims need a same-turn `gh pr view` receipt (Duty-6/#1431
   lesson, v0.4.91):** any claim that a PR was created, updated, re-pointed,
   or "auto-updated" by a push is UNVERIFIED until `gh pr view <n> --json
   headRefOid,headRefName,state` names the EXPECTED head sha and repo — a
   force-push to a fork branch does NOT move a PR whose head branch lives on
   another repo (#1431, 2026-09-07: "PR head auto-updated" claim dissolved on
   first-hand check; headRefOid was still the old rider sha). Check event +
   branch + head sha ALL match before concluding PR state.

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
2. Drift → re-read SKILL.md + editor.md in full from disk, then stamp
   `oc-ledger ack <your-roster-uuid> <new-version>` (shape `0.N.N`, `v`
   prefix tolerated — v0.4.55 fixed the N.N-only regex that made every real
   version un-ackable) — **ONLY when step 1 ran WITHOUT `--ack`**. With
   `--ack`, step 1 already wrote the adoption row (`oc-drift-check`'s `--ack` arm
   delegates to `oc-ledger ack`), so stamping here is a SECOND row for ONE
   adoption: **`--ack` IS the ack.** The canonical reload receipt is the
   single `oc-ledger ack` row — written once, by `--ack` if it was passed,
   otherwise by this hand-stamp. The ack row is the mechanical adoption
   record (HQ Duty 3 reads it for skew-chase). **ORDERING — a DRIFT verdict printed
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
5. **Tool discovery (owner order 2026-09-07, v0.4.94):** the table below is
   the role-DAILY subset, not the inventory — the full tool list
   lives in `tools/docs/RC-CONTRACT.md` (every tool: invocation, rc register,
   selftest owner). Before hand-rolling any check, grep
   tools/docs/RC-CONTRACT.md for a purpose-built tool — verification, audit, smoke,
   artifact and log work especially: a tool likely already exists.
6. **PATH anchoring (v0.4.130, ruling n=2369):** the oc-* tools are NOT on
   the lane shell's PATH — never invoke them bare and never `which` them
   (empty result ⇒ the rc=127 discovery class, first catalogued 2026-09-06).
They are path-invoked skill scripts. Canonical anchor:
`~/.opencrabs/profiles/ops/skills/opencrabs-dev/tools/<group>/<tool>` — the fleet is
grouped one level per FUNCTION (`audit/` `git/` `harvest/` `issue/` `notify/` `ship/`
`smoke/` `state/`); relative `tools/<group>/<tool>` forms in these docs assume the skill
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

Canonical descriptions + selftest contracts: `tools/docs/RC-CONTRACT.md` (full
inventory of tools) + SKILL.md tool table. The
editor-relevant daily subset, invocation forms only (all paths relative to the skill
dir; actor derived automatically from ambient `$OPENCRABS_SESSION_ID`):

| Tool | Invocation | For |
|------|-----------|-----|
| `oc-start` | `tools/git/oc-start <issue-N> --branch <branch>` | Milestone 1: atomic issue claim + branch + worktree setup |
| `oc-ship-chain` | `tools/ship/oc-ship-chain --sha <sha> --branch <branch>` | Milestone 2: single-invocation gate → comment → ff-merge → carrier build → live swap |
| `oc-smoke` | `tools/smoke/oc-smoke <issue-N> [--probe "<cmd>"]` | Milestone 3: unified 4-leg smoke verification & verdict logging |
| `oc-commit` | `tools/git/oc-commit -m "<msg>" [--issue N]` | Gated SIGNED commit: Session-Id + Issue-Ref trailers derived from session ID + ledger claim |
| `oc-drift-check` | `tools/state/oc-drift-check <your-uuid> [--ack]` | §Mid-cycle skill drift pull-check on detached resume |
| `oc-issue-sweep` | `tools/issue/oc-issue-sweep '<query>' [--fork R]` | Phase 1 uniqueness gate (fork open+closed + upstream closed) |
| `oc-ledger` | `stamp claim --what "…"` · `ack <uuid> <0.N.N>` | Roster receipts + version ack |

*Note: Underlying plumbing tools (`oc-wt`, `oc-deploy`, `oc-prchecks`, `oc-issue-log`, `oc-attrib`, `oc-pr-fault-scope`) are orchestrated internally by `oc-start`, `oc-ship-chain`, and `oc-smoke`.*

Rules that outlive any table: journal read-back after every `oc-ledger`
claim/stamp (Phase 1 step 4); terminal truth = `gh run view --json conclusion`, never
a tool's exit code alone; the ≥30s detached-poll floor (fleet-directives.md §CI-wait discipline & actor attribution).

## Phase 0 — Fresh base

```bash
git -C ~/opencrabs fetch origin && git -C ~/opencrabs fetch adolfousier
```

- Branch off fresh `origin/main`; merge-sync RETIRED (canonical REBASE model 2026-09-11 —
  SKILL.md §Upstream relations): NEVER `merge --ff-only adolfousier/main` into
  the shared checkout.
- **The shared `~/opencrabs` checkout is NEVER evidence** (v0.4.5): it may sit on any
  session's leftover branch. Verify shipped behavior against `origin/main`
  explicitly (`git fetch origin && git show origin/main:<path>`) or in a fresh
  worktree cut from `origin/main` (lens B F2, v0.4.79 — completed truncated rule).
- Before building on an existing branch: diff it against its merge-base to confirm no
  foreign WIP rode along from parallel agents. Take a backup branch ref before any
  `rebase --onto`. *(SKILL.md §Shared war stories)*
- **Checkable Completion Formula**: `DONE = Remotes origin and adolfousier fetched + origin/main tip verified.`

## Phase 1 — Claim & Worktree Setup (`oc-start`)

0. **Claim-time fresh re-read & Goal Mandate (v0.4.14 / v0.4.149, owner order 2026-09-12)**:
   - **Fresh Re-read**: FIRST action after claiming/waking — re-read `SKILL.md` + `editor.md` + `fleet-directives.md` from disk (never from recalled memory) — SKILL.md and editor.md in FULL, fleet-directives at thematic-index minimum with every `[LANE]`-tagged section in FULL. DONE = all three files re-read THIS turn.
   - **Design-gate precondition (owner order 2026-09-12)**: Issue the goal **ONLY AFTER the owner has confirmed the design** (owner design gate, v0.4.128). While the design is unapproved the editor stays in the design/approval phase — an early `/goal` would carry it past the very gate that requires owner approval BEFORE code. Fixed sequence: design → owner confirms → `/goal` → continuous execution through Phase 6b.
   - **Autonomous Goal Mandate**: After the owner's design confirmation, the editor MUST execute `/goal follow the skill until the smoke test phase` (via `slash_command`). The Editor is mandated to drive autonomously and continuously from Phase 1 through Phase 6b smoke testing (claim → worktree → code → sign → ship via `oc-ship-chain` → live behavioral smoke test on swapped binary → record 4-leg smoke verdict in `smoke-verdicts.log`). **Editors MUST NOT stop or ask for confirmation after Phase 4 (writing code) or after intermediate ship legs.** The task is only complete once the live behavioral smoke test is recorded in `smoke-verdicts.log`.
1. **Uniqueness Gate**: Search existing issues first via `tools/issue/oc-issue-sweep '<query>'` (sweeps fork open/closed + upstream closed).
2. **Issue Creation & Continuous Relationship Linking**: file a `fix(`/`bug(`-titled issue via `tools/issue/oc-issue-create` declaring its origin ON the creating command -- `--parent <N>` for a fork feature issue, `--root upstream:<sha|PR|path>` where the surface is upstream-inherited (`upstream-rooted`), `--no-parent "<reason>"` as the last resort. A declared root or orphan is legal; a silent one is a violation.
   - If no issue fits, open ONE issue on the fork: `gh issue create -R leshchenko1979/opencrabs` (symptom + evidence).
   - **Continuous Relationship Linking Mandate (owner order 2026-09-16)**: Whenever parent subsystem relationships, blocker dependencies, or child sub-issues are known at creation or discovered in-flight during implementation, the editor MUST establish native links in the same turn via `gh issue edit <issue> --parent <parent-issue>` and/or `gh issue edit <issue> --add-blocked-by <blocker-issue>`.
3. **Atomic Claim & Worktree (Milestone 1 — `oc-start`)**:
   ```bash
   tools/git/oc-start <issue-N> --branch <type>/<slug>
   ```
   `oc-start` automatically executes:
   - Uniqueness check and ledger claim (`oc-ledger claim`).
   - Remote fetch and clean branch creation off fresh `origin/main`.
   - Clean worktree mounting at `~/oc-wt-<task>`.
   *(Manual fallback `oc-wt add <task> <branch>` is reserved only for raw non-issue worktrees).*
   - **ZERO-ACK ON DISPATCH (owner order 2026-09-13)**: When receiving a task dispatch (`[ISSUE TRIAGE DISPATCH: #N]`), **NEVER reply with a `session_notify` ack**. Running `oc-start` or stamping `oc-ledger claim` is the sole required action.

DONE = Issue verified/filed, atomically claimed on ledger, and clean worktree mounted at `~/oc-wt-<task>` on branch `<type>/<slug>` tracking fresh `origin/main`.

## Phase 2 — Worktree Lifecycle & Isolation

- **Exclusivity**: ALL edits happen in `~/oc-wt-<task>`, NEVER in the shared checkout. Parallel agents share the repository.
- **Inline Execution**: While holding an active worktree, ALL execution runs inline in the owning session (`isolated=false`). Auto-spawned isolated workers are forbidden.
- **Teardown**: After shipping via `oc-ship-chain` (Phase 5), remove the worktree:
  ```bash
  tools/git/oc-wt remove <task>
  ```
DONE = Worktree exclusivity maintained, edits isolated to `~/oc-wt-<task>`.

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

DONE = Full symbol graph & caller tree mapped via `memory_search scope="external"`, DRY reuse verified, and trait/API signatures confirmed via `grep_docs` before the first edit.

## Phase 4 — Shape the change

- One logical change per branch; drive-by refactors go to their own branch + issue.
- Stage only paths YOU changed: `git add <paths>`. Never `git add -A`, never `commit -a`.
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
touches the trailer area** (v0.4.71, Duty-4 P2). `git interpret-trailers --parse` (or a `gh api`
commit-body scan) must show every expected trailer before the sha enters any
gate or push.

**Test placement & upstream coding standards (CONTRIBUTING.md policy, Adolfo DM 2026-09-13):**
- Tests live under `src/tests/*_test.rs` registered in `src/tests/mod.rs`, never inline `#[cfg(test)] mod tests { ... }` blocks.
- `mod.rs` is for module declarations and re-exports ONLY — zero function definitions (`fn`) in any `mod.rs` (fork discipline, not a CI gate — see `fleet-directives.md §Upstream Coding & Testing Standards`).
- Commit trailers must never include `Co-Authored-By`.
- No `#[allow(dead_code)]` / `#[allow(unused)]` suppression; unused code must be deleted.
- If introducing, renaming, or retiring concepts, update `src/docs/reference/ONTOLOGY.md`. This is fork discipline, not a CI gate — do not cite it as a CI obligation (v0.4.211/v0.4.213).

**No local fmt exists — the fmt leg runs in CI only (v0.4.210).** `/root/.rustup` is gone from this host and `/usr/local/bin/rustfmt` was RETIRED 2026-09-19: it exits 1 `BLOCKED`. Do not invoke it, and do not hunt for a replacement. `pr-checks.yml` runs fmt as a **soft-fail** leg, so a formatting-only diff it reports on code that is already green is **KEEP AS-IS; fix only what you introduced yourself**. There is no local fmt or compile path at all: the first real check of a change is the CI gate.

**fmt-clean ≠ compiles — audit CALL-SITE SHAPE before you chain (v0.4.141).**
There is no local compile path on this box: `which cargo` prints a path, but
running it prints `BLOCKED` — *the presence of a path is not evidence of a
toolchain*, the same family as "an empty result from a wrong path is not a
verdict". Nothing local proves a change compiles or is formatted; the first real
check is CI — a full gate dispatch. Before `oc-ship-chain`, mechanically
cross-check every NEW or CHANGED call site against the callee's real definition:
**free fn vs associated fn** (a free-fn path on an associated fn is `E0425`),
the **receiver** (`&self` / `&mut self` / none), and **`Drop`-impl move rules**
(moving a field out of `&mut self` in `drop` is `E0507` — take it with
`Option::take()`).
DONE = Target change implemented, call-site shapes verified, and signed commit landed on branch with Session-Id trailer.

## Phase 5 — Ship (`oc-ship-chain`)

**`oc-ship-chain` IS the single, exclusive ship path from commit to swapped binary (v0.4.126; manual push-to-main, manual issue-log, and manual oc-deploy sediment retired v0.4.132).**
The Editor runs `oc-ship-chain` in one detached invocation under one chain-id — **armed in its OWN transient systemd unit, never via the harness's `background:true` auto-detach**:

```bash
# 1. Push your branch first
git -C ~/oc-wt-<task> push -u origin <branch>

# 2. Arm the chain in its OWN unit (resumes the session on finish)
systemd-run --user --unit=oc-ship-<issue>-$(date -u +%H%M%S) --collect \
  tools/ship/oc-ship-chain --sha <commit-sha> --branch <branch> [--issue <issue-n>]
```

**THE LAUNCH SURFACE IS LOAD-BEARING (measured 2026-09-26, lane 63d775f9).** Two consecutive chains armed via the harness's background mode died `rc=143` (SIGTERM) ~75 s after the wrapper exited 6 — **even though LAW 17's re-exec had already placed each in its own user scope** (`run-r02937f26c50b43bea91cb45c7ca6dc58`, `run-rd0e1dd4e3b404e09b861bb58a87a3e0a`; detached logs `747586` / `758792`, both ending `gate infra rc=143`). Swap, a peer's broad `pkill` and a ship-lock wait were each ruled out by same-turn reads. The identical chain armed with `--unit=… --collect` survives and polls. **The CAUSE is NOT established** — the discriminator is. And the cost of getting it wrong is not just a lost chain: the killed run leaves its gate **`in_progress` with nobody polling it**. Measured the same hour: `36277623534` and `36277682621`, both `status=in_progress` / `conclusion=null` — two wasted full gates.

`oc-ship-chain` executes the entire 5→swapped stretch mechanically:
1. **Leg 1 (CI Gate):** Dispatches and watches `oc-prchecks` (`pr-checks.yml` on your branch: fmt + clippy + `cargo test --locked --profile ci --all-features`). ⚠️ **The chain's DEFAULT gate is FAST, and FAST is NOT the CI-gate leg of the 4-leg rubric** (finding `127429e6`, cycle `20260919-c21`): `oc-ship-chain` passes `--fast` to `oc-prchecks` unless `--full`/`--no-fast` is given (`oc-ship-chain:30-31`, call site `:706`), and `--fast` runs **fmt + clippy only, tests skipped** (`oc-prchecks --help`, `:704`). A FAST run's job name carries the only visible marker (`… — FAST`) and its `Run tests` step reads `skipped` — citing that run as your CI-gate evidence leaves the smoke receipt with **no all-features test evidence at all**, the exact leg the "Corrected-code presence ≠ smoke success" law protects. Pass `--full` when the receipt needs the test leg, or dispatch `oc-prchecks` yourself without `--fast`. **Exception — a pure-docs commit SKIPS this leg** (owner ruling 2026-09-12: *"We don't need the pure docs commits to pass through ci on our side."*). "Pure docs" is defined in the law, not by the tool: every changed path ends `.md` **and** is not `include_str!`-compiled into the binary — the 21-path compiled-in exclusion set lives in `fleet-directives.md §Docs-Only LEG1 Gate Skip`. A skip is recorded as **SKIPPED** and is never a passed gate: do not cite a skipped leg as GREEN, and do not count it as a passed leg in a smoke receipt.
2. **Leg 2 (Issue Log):** If `--issue <N>` is supplied, posts the per-commit implementation comment via `oc-issue-log` automatically.
3. **Leg 3 (Fast-Forward Merge):** Fetches fork `main`, verifies fast-forwardability, and pushes `<branch>:main` (serialized via `ship.lock`).
4. **Leg 4 (Carrier Ship):** Dispatches `oc-deploy ship --sha <sha> --execute` to build on `ci/quick-build-linux`.
5. **Leg 5 (Swap & Seal):** Bounded-polls carrier execution (`oc-deploy poll --execute --wait <sec>`) until the binary is live and swapped. The ship wait default is **2700 s** (`OC_SHIPCHAIN_SHIP_WAIT`, tool text `oc-ship-chain:192`) — raised from 900 s at #336 after 11 of 37 carrier successes exceeded 900 s (10 most recent: 942-1344 s, median 1062 s). A shorter budget mislabels a still-building run as INFRA rc 6.

**Carrier Coalescence & Ancestry Matching (v0.4.148):**
Editors do not serialize on a pre-dispatch carrier lock. `oc-deploy` and `oc-ship-chain` accept descendant carrier builds via ancestry verification (`git merge-base --is-ancestor "$SHA" "$CAND_SHA"`). If multiple editors push in quick succession, GitHub Actions concurrency coalesces the queued runs into a single descendant build. Once that build completes GREEN, all merged ancestors are recognized as deployed. Host swaps are strictly serialized and monotonic via `host-swap.lock` and lineage checks.

There is NO legitimate manual exit point between gate verdict and swap. The #134 orphan class (stopping at GREEN without swapping) is structurally closed.

### Failure Modes, Tool Automations & Agent Recovery Protocol (v0.4.145)

When shipping features via `oc-ship-chain` or deploying via `oc-deploy`, failures and interruptions follow the mechanical automation vs. manual resolution contract below:

| Failure Mode | Return Code / Signal | What is Mechanical (Automated by Tool) | What Requires Agent (Semantic Fix) | Tool Output & Communication |
|---|---|---|---|---|
| **1. Non-Fast-Forward Push** | `rc=5` — **any** NON-FF, clean *or* conflicted | **Mechanical only on `oc-deploy`'s own push path** (cause (c) below, v0.4.145): it auto-fetches `origin/main`, rebases, audits with `oc-rebase-safety audit`, and retries the push in 3s. **`oc-ship-chain` does NOT rebase** — LEG3 is a bare `git merge --ff-only` that dies `rc 5` **unconditionally** on any non-FF, so LEG4 (and with it the auto-rebase) is never reached. | The **LANE** rebases `$BRANCH` onto fork main and force-pushes **before** re-running the chain — a **clean** non-FF still needs this; the table does NOT mean "wait for auto". A **semantic conflict** additionally needs hand adjudication. | `NON-FF: rebase <branch> onto fork main (oc-rebase-safety) and re-run` (chain) OR `REBASE_CLEAN` / `REBASE_CONFLICT` (**only** on `oc-deploy`'s push path). Canonical rc register: `tools/docs/RC-CONTRACT.md`. |
| **2. Carrier Compilation Failure** | `rc=3` (`build-failed`) | **Auto-log extraction**: Tool automatically runs `gh run view <id> --log-failed`, parses `error[E...]` and rustc diagnostic lines, and prints the exact compiler error and file:line in tool stderr. | Agent fixes the Rust syntax, borrow checker, or missing module error in the worktree, commits, and re-runs `oc-ship-chain`. | `CARRIER_BUILD_FAILED (rc=3): Run <id>` followed by extracted compiler error block |
| **3. Daemon Boot Panic / Swap Failure** | `rc=4` (`swap-failed`) | **Auto-rollback & Auto-diag**: `oc-deploy swap-execute` **automatically rolls back** to the previous binary (`/usr/local/bin/opencrabs.bak`), restarts the service, and automatically extracts the panic backtrace from `journalctl -u opencrabs-ops.service -n 30` into tool output. | Agent inspects the auto-extracted panic trace, reproduces/fixes the startup bug or bad unwrap in the worktree, commits, and re-chains. Host remains 100% healthy. | `SWAP_FAILED (rc=4): Auto-rolled back to previous binary. Daemon boot panic: <extracted log>` |
| **4. Daemon Bounce Task Interruption** | Restart signal / `[BACKGROUND TASK INTERRUPTED]` | **State file + recovery re-run** (⚠️ there is **no `--resume` flag** — `oc-ship-chain` dies `rc=2` on an unknown arg): `oc-deploy swap-execute` writes the deployment result to `/root/.opencrabs/profiles/ops/opencrabs-dev/deployed.sha`. Only the `poll --execute` path hands Phase B to a transient `systemd-run` unit, so a **direct** `swap-execute` runs in the caller's cgroup and can be killed by the very restart it performs. | **Recover by state, not by resume**: read `deployed.sha`; if the swap landed, confirm `disk==proc MATCH` and go to Phase 6b. If the chain died before the swap, **re-run the same chain with `--gated-run <id>`** (reuses the GREEN gate run whose job name pins your sha) — see `upstream-merge-runbook.md`. | `SWAP_SUCCESSFUL: running binary matches deployed SHA. Ready for Phase 6b smoke.` |

**Exit codes & Lane action:**
- **Exit 0 — SWAPPED:** The new binary is running live on the host (`opencrabs-ops` user unit). Worktree can now be removed (`tools/git/oc-wt remove <task>`). Proceed immediately to Phase 6b (Smoke-test-on-notify).
- **Exit 2 — USAGE:** Bad or missing arguments (`--sha`/`--branch` are required; malformed flag). Correct the invocation and re-run — no lane state to resolve.
- **Exit 3 — DIRTY CHECKOUT:** The fork checkout has uncommitted changes (pre-flight refusal). Clean or stash it, then re-run.
- **Exit 4 — GATE-RED / CARRIER-RED:** The CI gate failed or the carrier build failed. Start a fix round (Phase 6-Fix): keep the same branch, fix in a new worktree, commit, push, and re-run `oc-ship-chain`. Triage heuristics live in `SKILL.md §Red-run triage heuristics`. **Also the `--gated-run` / `--gated-sha` pre-verify failure:** the supplied run was not `completed success` on a job pinned to the sha, or `--gated-sha` did not match `--sha`. Do NOT re-dispatch the run — re-verify it with `gh run view <id> --json status,conclusion,jobs` and re-supply the correct id.
- **Exit 5 — NON-FF / MERGE CONFLICT · TIP-MOVED · REBASE-GATE:** THREE distinct causes share this code (tool text `oc-ship-chain:828-829`; full register in `tools/docs/RC-CONTRACT.md`). **(a) NON-FF / MERGE CONFLICT** — `oc-ship-chain` LEG3 ran `git merge --ff-only` and refused. A **clean** non-FF and a **conflicted** one are the SAME code from the chain's side: the chain performs **no rebase of its own**, so the LANE rebases `$BRANCH` onto fork main and force-pushes first; a **semantic conflict** additionally requires hand adjudication. (The automatic in-tool rebase belongs to `oc-deploy`'s own push path — that is cause **(c)**, not this one. Do not wait for an auto-rebase that the chain never runs.)
  ```bash
  git -C ~/oc-wt-<task> fetch origin
  git -C ~/oc-wt-<task> rebase origin/main
  # resolve conflicts in working tree
  git -C ~/oc-wt-<task> push --force-with-lease origin <branch>
  ```
  ⚠️ **`oc-rebase-safety` is NOT the rebase engine** — it is a READ-ONLY safety auditor (`audit` / `overlap`). Use standard git commands to resolve conflicts, verify zero lost edits with `oc-rebase-safety audit`, and re-run `oc-ship-chain`.
  - **(b) TIP-MOVED** — the branch was force-pushed mid-gate, so `$TIP != $SHA`: LEG3 refuses rather than fast-forwarding fork main onto a tip NO GATE VALIDATED. Recovery: re-run the chain against the new tip — do NOT land the ungated tip.
  - **(c) REBASE-GATE** — `oc-deploy`'s in-tool auto-rebase refused the push (`OC_DEPLOY_GATE=rebase-conflict` / `rebase-audit-failed`). Recovery: rebase `$BRANCH` onto fork main yourself, verify with `oc-rebase-safety audit`, then re-run.
- **Exit 6 — INFRA / ORDER-GATE:** dispatch or poll infrastructure failure (`oc-prchecks` rc 4/7/8, or ship rc other) — **or an ORDER-gate rejection post-push.** ⚠️ **The UNSIGNED case lands HERE, and it is NOT an infra fault:** a head commit carrying no `Session-Id` trailer is refused by ORDER gate 4 (`oc-order-validate: UNSIGNED … attribution mandatory`), and the chain exits 6. Read the message before you act — if it says UNSIGNED, do not go hunting for a network or carrier problem. Fix = land an empty trailer-signed marker commit on the head (tree-identical, forward-only; `upstream-merge-runbook.md` step 9) and re-run. Every synthesis/merge head is unsigned **by construction**, so this recurs on every sync. **A lineage-guard refusal ALSO exits 6:** `oc-deploy swap-execute` refusing a post-rewrite swap (`non-monotonic-swap`) surfaces here. Recovery = **re-run the same `oc-ship-chain` leg** — the guard is rebase-aware (v0.4.151) and accepts the swap as `rewrite-equivalent-swap`. **NEVER hand-edit `deployed.sha`** to re-point around a refusal (`fleet-directives.md §Post-Rewrite Swap Recovery`).
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
git -C ~/oc-wt-<task> fetch origin
git -C ~/oc-wt-<task> merge-base --is-ancestor <branch> origin/main || {
  git -C ~/oc-wt-<task> rebase origin/main      # hand-resolve any conflicts
  git -C ~/oc-wt-<task> push --force-with-lease origin <branch>
}
```

⚠️ **Distinguish this from the v0.4.214 local-main reconcile — same `rc 5`, opposite fixes.** v0.4.214 covers LOCAL `main` being stale while the branch is *correctly* based on `origin/main`: that is a FALSE alarm and the fix is **do not rebase**. This check covers `origin/main` having genuinely MOVED during the gate: the rebase is **real and necessary**. The v0.4.214 diagnostic (`git merge-base --is-ancestor main origin/main`) does not separate the two — test against `origin/main`, never against local `main`. Automating the re-check inside the chain (pre-LEG3) is a Toolsmith call; until it lands, the LANE owes the check.

**Gate-idle question sweep:** CI gate and carrier build waits are idle time — do not sit silent on open questions. Circle back to the user in your topic with anything unresolved (scope doubts, naming, approach forks) while the chain runs; waiting is never a reason to hold a question or to guess.
DONE = `tools/ship/oc-ship-chain` exited 0 (SWAPPED) with new binary running live on `opencrabs-ops` unit and worktree cleaned.

## Phase 6b — Smoke Verification (oc-smoke)

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
   **Checkable completion criteria (v0.4.170, Finding G-2):**
   DONE = Mechanical proof demonstrating target feature execution against the running binary (command output, log line with PID/timestamp match, or API receipt); confirmed via `tools/smoke/oc-smoke` (exit 0) and recorded in `smoke-verdicts.log`.
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
   `oc-harvest-census` and Triage intake. If the feature is COMPLETE,
   this same evidence goes to your forum topic and your obligation ENDS there —
   the HARVEST lane takes the port, the upstream gate and the filing
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

**Behavioral probe is the smoke PASS GATE (owner order 2026-09-08 12:16Z):**
lineage (is-ancestor), identity (`oc-smoke-evidence` MATCH) and CI gate
evidence do NOT constitute smoke PASS — they are bookkeeping legs. A smoke
verdict of PASS requires step 3 to have TRIGGERED the fix's actual runtime
path on the live box and observed it execute (real message round-trip, real
interrupt, real stamp — not CI test counts). If the fix has no observable
runtime surface, declare the probe N/A with the structural reason in the
smoke evidence (precedent: #92 no-runtime-string finding) — never silent-skip.
A verdict citing only legs 1–3 is INCOMPLETE and gets returned to the lane.
(A stripped binary that compiles the fix but crashes on the path must FAIL —
that is the exact hole this rule closes; origin: ship-38585459 smoke n=2036.)

**Owner-dependent leg → PARK, never wait (v0.4.152, owner order 2026-09-12):**
if the only remaining behavioral evidence needs the OWNER — a visual pass, a tap,
an eye-confirm on a card — the leg is **NOT a blocking gate**. Stamp the legs you
can prove (lineage, identity, CI, any agent-runnable probe), append a
`PARKED-OWNER-EYE` row to `smoke-verdicts.log` naming the owner action required
and the packaging sha, then **RELEASE the lane** and move to your next task. A
lane idling on an owner leg is in violation; a lane that parks and moves on is
compliant. Owner-absent windows (nights) are exactly when this binds. Owner
verdicts must be explicit AND post-hoc — a passing remark made mid-flight is not
a verdict (row 87 → row 90: the owner's "Smoke passed" landed 16 s after their
own discard and 3 m 17 s before the review finished, so it certified a defect
that did not yet exist; the PASS was revoked). If the remark is ambiguous, record
`OWNER-REMARK (not a verdict)` and leave the leg OPEN/PARKED. Full law:
`fleet-directives.md §Owner-Dependent Smoke Legs — Park, Don't Chase`.

**Swap timing is NOT coordinated with smokes** (owner decision, closing editor
proposal #8): NO advance announce, NO swap delay — deploys land whenever the
pipeline is ready, even mid-smoke; loss of in-flight in-memory state is ACCEPTED
until Alexey fixes it otherwise. If a bounce kills your smoke mid-run: re-arm tool
schemas (step 1), re-run from scratch — NEVER report the bounce itself as a feature
FAIL.


### Smoke-verdict rules (moved from SKILL.md §Test ontology, v0.4.262)

Re-homed by cycle `20260925-c24` lens B (B-H2): the always-loaded router carried the smoke
PROCEDURE under its ontology table. The ontology (the three kinds + the sanity signal) stays in
`SKILL.md §Test ontology`; the verdict rules and their incident history live here, on the load path
of the role that actually produces smoke evidence.

The table above carries the content; what remains prose:

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
  nothing else (`tools/smoke/oc-smoke:9`, `:57`, `:64`), while these laws mandate
  tokens such as `UNPROVEN (presence-only)` and `PARKED-OWNER-EYE`. A lane
  ordered to stamp a mandated token through that writer therefore CANNOT: the
  row it produces says PASS or FAIL and the nuance is silently lost. So before
  citing a verdict token as *recorded* evidence, confirm the writer can emit it;
  when the mandated token is outside the writer's set, record it in the row's
  free text and STATE which form was used — never present a token the tool
  cannot produce as tool-emitted.

**Corrected-code presence ≠ smoke success (owner order 2026-09-08):** evidence
that the corrected code is merely PRESENT in the swapped binary — strings
marker hit, sha match, deployed.meta identity — can NEVER back a smoke-success
verdict on its own. Presence proves the artifact shipped; it says nothing
about behavior. A smoke verdict of GREEN additionally requires at least one
BEHAVIORAL probe of the corrected path actually executing (a live call, a
forced trigger, an observed output through the new code). If only presence
evidence exists, the verdict is `UNPROVEN (presence-only)` — never GREEN, and
the lane's ledger append must carry that label.

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

**Bookkeeping legs ≠ smoke PASS (owner order 2026-09-08 12:16Z):** lineage
(is-ancestor), identity (artifact==exe sha) and CI gate evidence are
bookkeeping legs — ALL THREE PASSING still does not constitute a successful
smoke test. Smoke PASS requires a live behavioral probe of the corrected
runtime path on the running box (full rule: editor.md Phase 6b). A verdict
citing only bookkeeping legs is INCOMPLETE — returned to the lane, never GREEN.


**Owner-dependent leg → PARK, never wait (v0.4.152, owner order 2026-09-12):** when
the only remaining behavioral evidence requires the OWNER (a visual pass, a tap, an
eye-confirm), the leg is NOT a blocking gate. Stamp the provable legs, append a
`PARKED-OWNER-EYE` row naming the owner action and the packaging sha, and RELEASE
the lane. A lane idling on an owner leg is in violation; a lane that parks and moves
on is compliant. Full law: `fleet-directives.md §Owner-Dependent Smoke Legs — Park,
Don't Chase` (L1–L4: parking, shift exit condition, owner-verdict timing, packaging-sha
stamps).

**Tool-description changes have no log-based probe (lane 1a63f103, 2026-09-12):** the
daemon's provider log records tool ARGS only (`[TOOL_ACCUM] name=bash`) and NEVER tool
schemas — so no log line can prove a description string was served. Smoking a
`Tool::description()`/`input_schema()` change uses **binary strings on the running exe +
the shipped constants in source**; any description fragment found in the log is
self-contamination from the prober's own commands. A "live schema served" receipt from
the log is a FALSE receipt.

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
**Duty-5 ruling 2026-09-19 (answering lane 4b0990b7, issue #295): for a SINGLE-SIDED probe the corollary IS the sufficiency test -- the discriminating negative half need not be OBTAINED, only NAMED and mechanically shown absent from the pre-fix tree.** A positive half alone backs PASS when all three hold: (1) the falsifying input is STATED explicitly; (2) its absence on the pre-fix artifact is established by a MECHANICAL discriminator run that turn -- `git log -S <string> <fix-sha> -- <pathspec>` returning exactly ONE introduction (the fix's own commit), or the string absent from `git grep` over the pre-fix tree -- never by assertion, never by reasoning about the code; (3) the probe observes the RUNNING artifact's OWN output (a live session's rendered prompt, a real call), and the observing session itself exercises the path under test (a Telegram-bound session, for a Telegram-delivery feature) -- a `strings` dump of the binary stays presence-only and cannot back PASS for a live-testable UX feature. What the corollary forbids is a probe that cannot NAME any input it would fail on: that probe measures its own constants. Where the negative half is STRUCTURALLY unobtainable -- prompts are rendered per turn and never persisted, so a non-Telegram session's prompt cannot be read back -- the mechanical discriminator of (2) stands in for it. **Carry the discriminator's command in the row.** **Scope it, or it proves nothing:** both sanctioned forms silently assume the token is GLOBALLY UNIQUE, which this law never stated. A non-unique token -- `MAX_ATTEMPTS`, `TIMEOUT`, `retry`, `attempts` -- makes form 1 return FOREIGN introductions and form 2 a false PRESENT. Measured on `96b474e` (lane c6b1a539, verified first-hand): `git grep -nEi 'max_attempts|backoff' 96b474e -- src/cli src/a2a` returns rc=1 with ZERO hits -- the correct pre-fix answer, the retry path is absent -- while the SAME grep UNSCOPED returns rc=0 with 265 hits, including a foreign `const MAX_ATTEMPTS: u32 = 3;` at `src/brain/agent/service/compaction.rs:348`. A CORRECT fix therefore FAILS its own discriminator, and the lane may wrongly conclude its probe is unsound. So the discriminator token MUST be PATHSPEC-SCOPED to the subtree the fix changes, the row MUST carry the pathspec, and "exactly ONE introduction" is a claim about a SCOPE -- never about the tree. **Anchor it too, or it proves nothing on a pre-merge tree:** form 1's revision defaults to HEAD, and a lane runs this discriminator on a PRE-MERGE tree where the fix's own commit is not yet reachable from HEAD -- so the bare form returns EMPTY, and empty reads as "no introduction exists": a FALSE NEGATIVE on the one tree the law is about. Form 1 is therefore ANCHORED at the fix's own commit -- `git log -S <string> <fix-sha> -- <pathspec>`. Measured on #450 (lane 2ed8adeb, verified first-hand; HEAD=main, fix `b6389c892` unmerged -- `git merge-base --is-ancestor b6389c892 HEAD` rc=1): the bare form returns EMPTY, the anchored form returns exactly ONE introduction, `b6389c892`. Form 2 is unaffected by this gap and is what established the negative half for #450 -- scoped, `git grep -c 'ProgressEvent::TokenCount' 33b7aecdd -- src/channels/telegram/resume.rs` returns rc=1 with ZERO hits (the correct pre-fix answer), while the SAME grep UNSCOPED returns 19 hits across 6 files, including the fresh-turn twin at `src/channels/telegram/progress.rs:1` -- a false PRESENT.


### Red-run triage heuristics (moved from SKILL.md, v0.4.262)

Shared diagnosis core, read by the editor in its fix round and by HQ in RED triage.
Re-homed by cycle `20260925-c24` lens B (B-H2).

## Red-run triage heuristics (shared core, v0.4.10 — moved from editor.md Phase 6)

ONE location: red-run diagnosis reads these (pre-S3: Compiler Step 2; now:
`oc-deploy` RED reports + HQ triage); the
Editor applies the same ones in its fix round (editor.md Phase 6c). No lane
uses them as a licence to fix outside its scope.

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

## Phase 6-Fix — Fix Loop (Red Carrier Build or Failed Smoke)

A RED `oc-deploy ship`/poll run or a failed smoke attributes the failure (via
`oc-attrib` Session-Id trailers) and routes the fix to the guilty editor WITH evidence.
Your answer is always the SAME sequence:

0. GATE — the bug must already HAVE an issue; the red-run hand-off names
   it. Missing? File it first (Phase 1 procedure). Fixing before filing
   violates the issue-first hard rule (SKILL.md).
1. **MANDATORY EXPLORATION & DRY GATE**: Before editing any files to apply a fix, you MUST run
   `memory_search scope="external"` over `/root/opencrabs/src/**/*.rs` to map callers,
   symbol definitions, and ensure no DRY abstractions are violated.

```bash
# 1. fresh worktree at the relevant sha (worktree lifecycle, Phase 2)
tools/git/oc-wt add <task> <branch>
# 2. reproduce → fix → SIGNED commit (E1, v0.4.78)
tools/git/oc-commit -m "<msg>"   # gated wrapper: Session-Id from ambient session ID, Issue-Ref
#    derived from your latest ledger claim, implementation comment folded in
# 3. push branch, then re-run oc-ship-chain (Leg 1 CI gate -> Leg 2 comment -> Leg 3 ff-merge -> Leg 4 carrier build -> Leg 5 swap)
git -C ~/oc-wt-<task> push origin <branch>
tools/ship/oc-ship-chain --sha <NEW-head-sha> --branch <branch> [--issue <issue-n>]
# 4. on exit 0 SWAPPED, remove the worktree — proceed to Phase 6b smoke re-test
tools/git/oc-wt remove <task>
```

**Per-commit laws live in their phases:** branch-attached HEAD + signing → §Phase 4; worktree-writer exclusivity → §Phase 2. They bind EVERY commit in ANY phase — read them there.
- **Checkable Completion Formula**: `DONE = Bug reproduced + memory_search caller check performed + fix committed with trailers + tools/ship/oc-ship-chain exits 0 (SWAPPED) + worktree removed.`


## Phase 7 + 7b — NOT the editor's → `harvest.md` (HARVEST lane)

Upstream PR filing (Phase 7) and PR lifecycle / blocker routing (Phase 7b)
**left the editor role** (owner order 2026-09-24 centralising harvest). Single
home: **`harvest.md`**, owned by the HARVEST lane. The editor's part ends at
smoke evidence — post it and hand the feature over. The PR SHIPMENT law's
procedure reference resolves in `harvest.md` (law home: SKILL.md §Hard rules —
ISSUE ROUTING bullet, PR SHIPMENT row).



## No auto-rollback on smoke FAIL (owner 2026-08-28 18:50Z)

Post-swap smoke FAIL → rollback is the OWNER's call, never mechanical. The swap-chain auto-rollback on post-bounce verify fail (crash-integrity: disk==proc mismatch → restore backup) is UNCHANGED — that one stays automatic. With deploy consent eliminated the same day, this is the only human gate left near the deploy pipeline.





