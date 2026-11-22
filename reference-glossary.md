# reference-glossary — official terms

> On-demand reference, moved verbatim out of `SKILL.md` §Glossary (2026-11-17).
> One concept = one name. A NEW concept is proposed via the poll format and named on owner
> word — never coined in a lane file, never a second name for an existing concept.

- **FIRE** — the release window between version bump and prod swap. The
  Duties-4+6 cadence threshold verdict (≥5 bumps/5 days) is a DISTINCT concept
  and must not carry this token: it is emitted as `CADENCE-FIRE`. The tool-side
  rename is a Toolsmith follow-up — until it lands, a bare `FIRE` in cadence
  output means the threshold verdict, never a release window.
- **carrier** — the single build lane: branch `ci/quick-build-linux` + its
  `quick-build-linux.yml` + dispatches from it. workflow_dispatch runs record
  the CARRIER ref/head, never the `-f ref` input; the carrier yml is the
  single source of truth for the prod feature set.
- **fan-out** — the automatic GREEN/RED notify fired at the swap_execute tail
  (`oc-deploy fanout`, idempotent via `fanout.state`).
- **state dir vs skill dir** — the v0.4.60 split: skill repo
  (`skills/opencrabs-dev/`, versioned code+docs) vs state dir
  (`opencrabs-dev/`, runtime). The state dir has NO tools/ — tools always
  resolve next to the invoking script.
  Its content is declared in TWO classes (v0.4.238, a RECOVERABILITY rule: a
  tracked file's only durable record is git):
  - **TRACKED** — `workers-ledger.json` · `journal/` · `oc-deploy/journal/`
    (the deploy audit trail `oc-deploy recover-receipt` reads) · the lane
    `*-state.md` records · `reviews/` · `evidence/` · `tools.log` ·
    `smoke-verdicts.log` · `deployed.sha`/`.meta.json` · `baseline.json` ·
    `fanout.state` · `base-red.json` (the BASE-RED marker store, #630) ·
    markers (`pacemakers-off`).
  - **GENERATED-IGNORED** — the generated class: `.bak`/`.bak-*` sidecars ·
    `.ledger.*` temps · `__pycache__/` · `*.pyc` · `*.lock`. Never committed,
    reaped on the hygiene cadence WITH a keep-window (a sidecar taken while its
    source was still UNTRACKED is the only copy of that reading).
  A TRACKED class's additions and updates MUST be committed by the state-repo
  commit path. That path has ONE home (#508, 2026-09-22): the `STATE_TRACKED_PATHS`
  and `STATE_TRACKED_GLOB` assignments in `tools/state/oc-ledger`, consumed by
  `state_sweep_tracked`, with a selftest asserting the single source. BOTH callers
  sweep the SAME namespace — the auto-commit tail and `commit-pending --bundle`.
  Consequence for authorship: a class named TRACKED above is only actually swept if it is in
  `STATE_TRACKED_PATHS` — naming it here without adding it there leaves it
  accumulating while the law reads as covered.
- **single-flight** — the one dispatch/adoption lock serializing concurrent
  oc-gate invocations; under it, the newest carrier dispatch is this
  lane's own run.
- **CI gate** — the `pr-checks.yml` dispatch on a worktree/PR head branch:
  fmt (soft-fail) + clippy + all-features test. The ONLY code-test locus.
  Legacy synonyms "CI lint gate" / "lint gate" / "UPSTREAM CI TRIAD GATE"
  all mean THIS gate ("the triad" = fmt/clippy/test); the named rule
  UPSTREAM CI GATE (SKILL.md) is this gate run before any upstream PR.
- **ORDER gates** — the 4 pure-git pre-dispatch checks inside
  `oc-deploy ship` (SHAPE / EXISTENCE / CONTAINMENT / SIGNATURE); no cargo.
- **S2 / S3** — deploy pipeline stages: S2 = sha-bound poll + auto-swap on
  GREEN; S3 = live cutover 2026-08-28 (swap chain mechanical, consent
  eliminated). Rules saying "below S2"/"S3" mean the stage gate.
- **Lane** — one editor session (worker) owning one fork issue + its topic.
  (v0.4.89, lens A7: extended to any role session — Triage/TOOLSMITH/HQ
  lanes exist too; "lane" ≠ editor-only.)
- **disk absorption** — the v0.4.19 worker-update model: skill files are plain
  disk; workers absorb re-reads at their own boundaries (turn start, role-file
  load), no reload pings are owed or sent (defined here lens A16 v0.4.89;
  used in editor.md/triage.md/toolsmith.md).
- **Triage lane** — the interrupt lane carved out of HQ at v0.4.86 (fix routing,
  enforcement patrols — `triage.md`); never edits skill files.
- **Toolsmith lane** — the CLI tool lane carved out at v0.4.87 (owner "Go toolsmith" 2026-09-06): owns
  `tools/` code — makes + fixes the CLI tools every other role uses (`toolsmith.md`); never edits skill
  markdown. (Discover EITHER session via `session_search`, never uuid-from-memory.)
- **Roster** — the worker registry in `workers-ledger.json` (enroll / claim /
  ack rows); `oc-attrib` joins Session-Id trailers against it.
- **Lens (Reviewer A–J)** — one Duty-6 read-only review perspective
  (catalog + full briefs: `review-lenses.md`; factory-side summary: `hq.md §Duty 6`).
- **HQ** — the skill-owning lane. The former name *Supervisor* is RETIRED
  (owner order 2026-09-11 folded the term into HQ — one role, one term);
  unofficial variants ("Author lane", "Carrier") seen in lane files are also
  retired — lens A-L3 v0.4.116.
- **Selftest** — a tool's built-in test mode (`oc-deploy --selftest` etc.);
  **battery** — `tools/tests/run.sh` across all tools. Both green before
  ANY version bump.
- **GREEN / RED** — a GitHub Actions run conclusion read by terminal truth
  (`gh run view --json conclusion`), never exit-code inference.
- **TOOL_ACCUM** — the per-session tool-usage rows accumulated in the unified
  tools log; evidence base for Telegram surface-law audits (triage.md Duty T4
  — ex hq.md Duty 7).
- **PARKED-OWNER-EYE** — non-blocking smoke row state (v0.4.152) stamped when
  the sole remaining behavioral evidence requires the human owner (visual pass,
  tap, UI inspection); frees the lane to continue or complete without blocking.
- **4-Leg Smoke Rubric** — the mandatory verification standard (v0.4.104) for
  shipping candidates: (1) Lineage (`git merge-base --is-ancestor`), (2) Identity
  (`oc-smoke-evidence` artifact checksum), (3) CI Gate (GREEN run on head sha),
  (4) Behavioral Probe (executing live binary path or structural N/A). All four
  must pass before an upstream PR leaves a lane.
- **issue cluster** — the harvest unit: fork-only commits grouped by their
  canonical issue ref, filtered on the ISSUE TITLE for fix-type. The dependency
  leg is the **UNION of TWO graphs** (owner ruling 2026-09-25) — the COMMIT/FILE
  graph AND the gh relationship graph — and they do NOT behave alike: only
  **1-HOP** file overlap is usable as a leg, because transitive closure collapses
  the whole delta; the gh graph is sparse and semantic but structurally weak while
  parent-linking is unenforced (13 of 55 open fix-titled clusters carry a parent).
  A set is **READY** iff (a) the most recent swap among its ready members is >24h
  ago AND (b) it has **no unready members**, where ready = swapped + smoked +
  **closed**. **THE TARGET IS EXCLUDED FROM ITS OWN READINESS SET** (HQ ruling
  2026-09-26, `n=11674`): the issue BEING harvested never gates itself; its **gh
  relatives** do. Including it was **circular** — closure is the harvest's OUTPUT
  (`triage.md §Autonomous closure`), never its precondition. Residual (mutually-linked pair): `upstream-merge-runbook.md §Cluster readiness`.
  Defined by `tools/harvest/oc-harvest-census clusters`, which derives it and emits
  every cluster (never pages silently); the soak gate keys on it and Triage surfaces
  by it. NOT "convergence cluster" (a Duty-4/6 group of rule proposals merged
  into one law change) and NOT a retired freeze T-group (the register was
  removed 2026-09-24); the bare word "cluster" in harvest law always means
  this one.

- **upstream-rooted** — a fix whose surface upstream shipped and we inherited; its ROOT is an upstream object
  (`--root upstream:<sha|PR|path>`, which must resolve), not a fork feature issue. Declared, never "an orphan".
