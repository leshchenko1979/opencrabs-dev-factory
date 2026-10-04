# opencrabs-dev

Operational skill for **OpenCrabs source work** on `~/opencrabs`: the fork
(`leshchenko1979/opencrabs`), upstream contact (`opencrabs/opencrabs`, PRs only),
CI carrier lanes, artifact builds, and binary swaps to `/usr/local/bin/opencrabs`.

Skill entry point: `SKILL.md` — invoked as `/opencrabs-dev`.
This README is the repo map; **SKILL.md is the law.** Where they disagree, SKILL.md wins.

## Layout

| Path | What it is |
|---|---|
| `SKILL.md` | Main entry: roles, hard rules, tool register, ship path, glossary |
| `editor.md` | EDITOR role procedure — Phases 0–6b (issue claim → worktree → edit → gate → commit → ship → smoke) + a Phase-7 pointer; the editor's obligation ENDS at smoke evidence |
| `harvest.md` | HARVEST role procedure — Phases 7 / 7b / 7c (feature complete → upstream PR → PR lifecycle → mechanized harvest) |
| `hq.md` | HQ role — worker roster, duty cadence, review lenses, issue triage |
| `triage.md` | TRIAGE role procedure — intake & assignment, dispatch hygiene, hygiene patrols, upstream lifecycle tracking |
| `toolsmith.md` | TOOLSMITH role procedure — owns `tools/` code, battery stewardship, tool-problem reports |
| `review-lenses.md` | Full Duty-6 lens briefs (A–J) — split from hq.md v0.4.78 |
| `war-stories.md` | Incident histories behind the hard rules (disclosed from SKILL.md, v0.4.80) |
| `fleet-directives.md` | Binding owner directives that apply to EVERY lane — the `[LANE]` cross-role law + a residual of cross-cutting rulings, with a pointer table to the role/topic file that owns scoped law. Re-homed from ops AGENTS.md/MEMORY.md, 2026-09-02; split 2026-09-18 |
| `upstream-merge-runbook.md` | Procedure for the REBASE sync model: gates, roles, conflict classes, migration-union rule |
| `s2-swap-journal-spec.md` | Journal vocabulary spec for the oc-deploy swap leg |
| `session-notify.md` | `session_notify` TOOL mechanics — split from SKILL.md v0.4.262 (the delivery LAW stays in fleet-directives) |
| `environment.md` | Shared environment facts for `~/opencrabs` — split from SKILL.md v0.4.262 |
| `CHANGELOG.md` | Version history, **newest entry FIRST** |
| `tools/` | The `oc-*` tool fleet, grouped by function (`audit/` `git/` `harvest/` `issue/` `notify/` `ship/` `smoke/` `state/`) |
| `tools/instruments/` | Corpus-agnostic analysis instruments — NOT fleet tools, so they carry no `oc-*` name |
| `tools/lib/` | Shared shell libs: `oc-log.sh` (journal + rc register + flood guard), `oc-embed.sh` (job-embed decoder) |
| `tools/docs/RC-CONTRACT.md` | SOLE per-tool rc register: fleet conventions + verdict codes (v0.4.78) |
| `tools/docs/HEALTH-CHECKS.md` | Systematic health checks registry for the tool fleet |
| `tools/docs/HEALTH-CLASSES.md` | Health classification taxonomy and remediations |
| `tools/tests/run.sh` | Battery: full selftest suite + coverage sections. Receipt → `tools/tests/battery-last.json` |
| `tools/archive/compiler.md` | ARCHIVED runbook for the retired COMPILER role (re-enable = load this file) |

## Roles

| Role | State | Runs |
|---|---|---|
| **EDITOR** | live | Fork issues, per-task worktrees, CI gates, signed commits, `oc-deploy ship` |
| **HQ** | live | Worker ledger, duty cadence, multi-lens code/structure reviews, direct directive proposals |
| **TRIAGE** | live (v0.4.86 carve-out) | Issue assignment, repo hygiene patrols, rebase/merge execution, upstream lifecycle tracking (folded from Harvester v0.4.176) |
| **TOOLSMITH** | live (v0.4.87 carve-out) | Owns `tools/` CODE — makes and fixes the CLI tools every other role uses, direct recipient of tool quirks/defects (v0.4.176) |
| **COMPILER** | **RETIRED 2026-08-28** (S3 cutover) | duties absorbed by `tools/ship/oc-deploy` (ship / poll / swap-execute) |

## Tool fleet (quick index)

Full register with rc codes lives in **`tools/docs/RC-CONTRACT.md`** — that file is the source of truth (v0.4.79; SKILL.md carries purpose rows only).
Highlights:

- `oc-deploy` — ship / poll (fused `--wait N` bounded poll, v0.4.100) / swap-execute / fanout
- `oc-ledger` — worker ledger: claims, `claims` verb, sync, version stamps, cadence
- `oc-prchecks` — CI-wait on `pr-checks.yml` (poll, resume-before-dispatch, lane gates; `--notify` is RETIRED)
- `oc-waiter` — RETIRED v0.4.135 (stub only: `--help` rc 0, every subcommand rc 1). Detached waits run natively — bash `background: true`, and the harness wakes the caller with the exit code; for cross-session chaining use `tools/lib/oc-notify.sh`
- `oc-notify.sh` (tools/lib) — shared wake/notify contract (sourced by `oc-deploy`; also an executable CLI wrapper for cross-session chaining)
- `oc-attrib` — Session-Id attribution; `--contributors` is the single contributors shape (oc-deploy contributors retired v0.4.90)
- `oc-commit` / `oc-issue-log` — signed commits + tracked-issue receipts
- `oc-seal-state` — order rows (QUEUED…VOID lifecycle)
- `tests/run.sh` — run everything: `bash tools/tests/run.sh`

  The tool inventory and every tool's exit-code contract live in `tools/docs/RC-CONTRACT.md`.

## Ship discipline (per version bump)

1. Edit → verify → commit (one logical change per commit, `Issue-Ref:` trailer).
2. Battery GREEN: `bash tools/tests/run.sh` → receipt reads `PASS`.
3. `CHANGELOG.md` gets a `## vX.Y.Z` entry (prepended at the top, newest-first).
4. Bump `version:` in `SKILL.md`, commit, tag `vX.Y.Z`.
5. `tools/state/oc-ledger sync --version X.Y.Z --why "..."` (gates on the battery receipt + changelog entry).
6. Push skill mirror (main + tag); state mirror parity sweep.

## Conventions

- **Bare `#N` is fork-issue space.** On any upstream surface, qualify: `leshchenko1979/opencrabs#N`.
- **CHANGELOG is newest-FIRST.**
- **Every tool journals.** State changes write timestamped lines to `tools.log` via `oc-log.sh` before the next step; a run unreconstructable from durable state is not done.
- `battery-last.json` is committed on purpose — it is the durable ship receipt.

## Repo status

Mirrored to `leshchenko1979/opencrabs-dev-factory` (renamed from `opencrabs-skill` 2026-10-03; pushed on owner word; state repo `leshchenko1979/opencrabs-dev-state`).
Current version: **`SKILL.md` frontmatter `version:`** — single source of truth, never stale (lens A M2, v0.4.79). Tag history: `git tag --list 'v0.4.*'`.
