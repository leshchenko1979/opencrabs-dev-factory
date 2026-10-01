# Environment facts (split out of SKILL.md, v0.4.262)

**Owns:** the shared environment facts every role needs when working in `~/opencrabs` —
repo topology, the `gh` default-repo trap, the skill glob gate, branch namespaces, the
build/carrier surface, and the daemon facts.

**The hard rules among them — the local-cargo ban and `gh -R` — are stated in
`SKILL.md §Shared environment facts (all roles)` and bind regardless.**

## Environment facts (all roles)

- **Actor attribution is automatic via ambient `OPENCRABS_SESSION_ID` (v0.4.176):**
  `lib/oc-log.sh`, `oc-commit`, `oc-ledger`, and tool scripts derive `actor:` directly
  from `$OPENCRABS_SESSION_ID` (commit `978fe5fe`). Manual `export OC_ACTOR` is retired.
  **If it is exported anyway it must be the BARE uuid** — a `<role> <uuid>` value
  passes `oc-commit`'s presence-only guard and lands the role word in the
  `Session-Id` trailer, which `oc-order-validate` gate 4 reads as UNSIGNED
  (measured 2026-09-26: ship rc 2, main stranded undeployed).
- Checkout `~/opencrabs`: remote **`origin`** = fork `leshchenko1979/opencrabs`
  (push target) · remote **`adolfousier`** = sync source (upstream).
- **`gh` in `~/opencrabs` defaults to UPSTREAM — `-R` is MANDATORY (2026-09-22).**
  The fork remote carries NO `gh-resolved` key while `remote.adolfousier.gh-resolved
  base` does, so gh's resolver selects upstream `adolfousier/opencrabs` for ANY command
  run from that directory without `-R` / `--repo`. It fails SILENTLY in both directions:
  a number that exists upstream returns a REAL but WRONG issue, and one that does not
  404s and reads as "no such issue" — while a write (`gh issue close` / `comment` / `edit`)
  lands on the OWNER'S UPSTREAM REPO. Measured 2026-09-22 from that cwd: unscoped
  `gh issue list --state open` → 9 (upstream), `-R leshchenko1979/opencrabs` → 144;
  `gh issue view 340` 404s unscoped and resolves scoped. Every prescribed `gh` command
  in this corpus already carries `-R` (14 sites) — this bullet states the RULE they were
  silently following. The environment fix (`gh repo set-default`) rewrites shared repo
  config and is the OWNER's call, never a lane's.
- **A `--branch` filter and a `headSha` scan are BLIND to a PR-lane sha BY
  CONSTRUCTION (editor lane 95bec69b + triage, 2026-09-27 — three lanes, one day,
  two of them reaching the same false "never gated").** `pr-checks.yml` is
  `workflow_dispatch`, so on EVERY run `headBranch` is `ci/quick-build-linux` and
  `headSha` is the **CARRIER head** — never the `-f ref=` input. The gated sha lives
  in the **JOB NAME ONLY**:
  `gh run view <id> --json jobs --jq '.jobs[].name'` →
  `gate / PR-lane gates (64b906b274aecfeba6803564f3a49740cbf883f1)`.
  **A zero from either blind query is NOT evidence the ref was never gated** — it is
  an instrument that cannot register the class. Read the job name. `oc-prchecks`
  self-documents the caveat (`headSha is the carrier head, not the dispatch input`),
  so the tool is not the defect — **believing the blind zero is.**
- **Before quoting ANY counter as a clearing receipt, state the mechanism by which
  the alleged event would REACH it.** A `workflow_dispatch` run's `headSha` cannot
  carry a PR-lane sha at all, so its zero is structural, not exculpatory. Same family
  as the `gh` default-repo trap above: both return a confident answer for a class
  they are blind to, and both were believed.
- **The skill glob GATE matches PATHS, not intent (v0.4.243, cycle
  `20260922-c22`).** A skill whose `SKILL.md` declares a `globs:` frontmatter key
  guards its own topic: any tool call whose harvested path tokens match one of
  those globs — matched against the NORMALIZED ABSOLUTE path — is REJECTED while
  the skill body has not been seen in this session. Harvested keys are `path` /
  `file_path` / `filePath`, plus path-like tokens inside a `bash` command;
  `grep`'s and `glob`'s own `pattern` key is deliberately NOT harvested ("a glob
  pattern string is not a path"). Five consequences a lane must know before
  reading a rejection: **(a)** it is a glob verdict about a PATH, never a verdict
  about intent — an unrelated call that merely names a matching path is gated all
  the same; **(b)** it re-arms after EVERY compaction (owner decision 2026-09-10),
  so post-compaction the skill is unseen again even if you loaded it earlier the
  same session; **(c)** recovery is `load_brain_file '<slug>'` or `read_file` on
  the skill's own source path — BOTH are exempt, and `load_brain_file` marks the
  skill seen exactly as the gate's own bookkeeping does — then re-issue the
  IDENTICAL call (the retry is armed before the rejection returns); **(d)** the
  body appended to a rejection is NOT a complete read, because tool output is
  capped and a long skill arrives as a head/tail preview — read it with an
  explicit `max_output_bytes`, or via `load_brain_file`; **(e)** the gate FAILS
  OPEN, so a rejection you did NOT receive proves nothing about the path — it
  means no globs were declared, the skill was already seen, or an internal error
  passed the call. Source of these semantics: `src/brain/tools/skill_gate.rs`
  (issue #150).
- BUILD SOURCE = fork `main`. Editors fast-forward their signed commits into
  `leshchenko1979/opencrabs@main`; `oc-deploy ship` dispatches THAT ref — every
  artifact compiles all editors' merged changes TOGETHER (decision 2026-08-25).
  Building upstream/adolfousier refs is the exception, explicit ask only.
- Branch NAMESPACES are reserved so any role can tell development from upstream
  PR heads at a glance (decision 2026-08-25): `<type>/<slug>` with type ∈
  `feat|fix|ci|chore` = DEVELOPMENT — fork-only, ff-merged into fork `main`
  (editor Phase 5 `oc-ship-chain`), archived after merge · `leshchenko1979/<slug>` = UPSTREAM PR HEADS ONLY (renamed from `up/*`, decision 2026-08-27)
  — created solely in harvest Phase 7 off `adolfousier/main`, never merged into
  fork `main`, never a dispatch source. Any lane reads the prefix and knows
  what it is looking at.
- This box has **no sanctioned Rust toolchain** — CI is the only sanctioned
  compile/test executor (Compiler role RETIRED 2026-08-28). No cargo/rustc/clippy in ANY form —
  install, PATH-prepend, explicit path, even an invocation that exits 0 is a
  violation. **Canonical full law: `editor.md §Box law — no local cargo, ever`** (Duty-6 c25 A-8:
  one home, pointers everywhere else). **No local tool exists at all** — `/root/.rustup` is gone and the
  `rustfmt` wrapper was RETIRED 2026-09-19 (exits 1 `BLOCKED`), so fmt runs only
  in CI as the soft-fail leg of `pr-checks.yml`; **cosmetic diffs it reports on
  CI-green code are KEPT AS-IS, not applied — fix only formatting artifacts you
  introduced yourself**; modum RETIRED 2026-08-28; lint evidence =
  GREEN pr-checks.yml run. Full ban list: editor.md §Box law (canonical;
  "(box law)" tags elsewhere refer to it).
- Daemons run as systemd **user** units (`systemctl --user`) — system-scope queries
  (`systemctl`, `/etc/systemd`) find nothing. (Binary path: `which opencrabs`.)
- Daemon PID identity (v0.4.15): NEVER `pgrep | head -1` — three daemons share
  this box (family, default, ops) and pgrep can grab the wrong one. The ops unit's
  PID comes only from `systemctl --user show opencrabs-ops -p MainPID --value`.
- Builds are MINIMAL-FEATURE by design: `cargo build --locked --profile ci
  --no-default-features --features "<set>"` *(profile ci = thin LTO /
codegen-units=16 — carrier yml since fork 8994be14)*. Upstream #1186 (missing #[cfg]
  gates) CLOSED 2026-08-25 — feature subsets compile clean.
- The feature set is PARAMETRIZED (`ebf44f69`, 2026-08-25): a workflow_dispatch
  input `features` (comma-separated). Its **`default:` in the workflow yml on the
  CARRIER branch `ci/quick-build-linux` is the SINGLE SOURCE OF TRUTH** for what we
  ship — these skill files NEVER copy the set (drift killed 2026-08-25). Read it
  live with `tools/ship/oc-carrier-features` (the reader oc-deploy itself resolves
  through).
  Changing the pick later = one-line Editor commit to that yml's `default:` —
  skills untouched.
- Dispatch ALWAYS passes the set explicitly: `-f features=<set>` (decision
  2026-08-25), even though a safe default exists. Artifact name carries the set:
  `opencrabs-linux-amd64-<set>`; job: `Linux amd64 (<ref>, <set>)`. The binary
  FILENAME stays `opencrabs-linux-amd64` (swap scripts depend on it). Anything
  outside the set (local-stt/local-tts voice, whatsapp/discord/slack/trello,
  pdfium…) is absent from the swapped binary — missing-feature behavior afterward
  is expected, not a bug.
- ORDER and dispatch carry sha AND feature set (v0.4.15, proposals P7+P8): a bare
  sha cannot identify WHICH build is meant under single-flight. The carrier yml has
  NO `--all-features` path — the build step hardwires `--no-default-features --features "$features"`
  — optional features order ONLY as `features=<comma-set>`, and a different-set build
  of the SAME sha is a DISTINCT build, serialized by the single-flight invariant.
- `source_ref` accepts a branch NAME (`main`) or the FULL 40-char commit sha —
  NEVER an 8-char short form: actions/checkout treats it as a glob and fetches a
  branch literally named `<sha>*`). PASS THE FULL SHA ALWAYS —
  see next rule for why it is now the only auditable record of what was built.
- The workflow lives ONLY on the carrier branch `ci/quick-build-linux` (moved off
  fork `main` 2026-08-26, Alexey's call — mirrors upstream dropping it from their
  main). Dispatch pattern adds `--ref ci/quick-build-linux`. CONSEQUENCE: the run
  object's `headSha` reports the CARRIER tip, not the built tree — the built
  commit is verified via the JOB NAME, which embeds `(source_ref, features)`.
  Carrier branches NEVER merge to `main` (same reservation discipline as `leshchenko1979/*`).
- **ALL fork CI lives on the carrier branch — `main` carries UPSTREAM's workflows, not ours**
  (owner correction 2026-10-01T01:11Z: *"the forks ci files live on a special branch"*).
  Measured: `origin/main` carries exactly `auto-assign.yml` `ci.yml` `prerelease.yml`
  `release.yml`; the fork's OWN CI — `pr-checks.yml` (the PR-lane gate), `ci-lane-impl.yml`
  and `quick-build-linux.yml` (the carrier build) — exists ONLY on `ci/quick-build-linux`.
  `main`'s `ci.yml` is **byte-identical to upstream's** (`git diff adolfousier/main origin/main
  -- .github/workflows/ci.yml` is empty) and its jobs resolve `self-hosted` on a push (the
  ternary yields `ubuntu-latest` only for a fork PR); the fork has **0 registered self-hosted
  runners**, so every main-push run queues indefinitely and is cancelled by the next push —
  measured 2026-10-01T01:17Z: **0 success / 58 cancelled** since 2026-09-14, the newest still
  `pending` on the `a85740948` push. **CONSEQUENCE — fork `main` has NO post-merge CI net**, by
  design (the CI files moved off `main` 2026-08-26, Alexey's call, mirroring upstream dropping
  them from theirs): the PRE-merge PR-lane gate (`oc-ship-chain` LEG1) is the ONLY gate, and
  the only thing between a red commit and the carrier build. **Never read `main`'s workflow
  files as evidence about the fork's CI, and never "repair" them** — they are upstream's; editing
  one is divergence that conflicts on every upstream sync.
