# TRACKER ROUTING — which GitHub repo each `tools/**` site targets

**Owns:** the per-site tracker decision for the two-stream issue-routing law
(SKILL.md, v0.4.284, owner order 2026-10-03 21:17Z). Records WHAT each tool
targets and WHY, so a later reader does not have to re-derive it.

**Law (verbatim, SKILL.md):**

| stream | tracker | what belongs there |
|---|---|---|
| **BINARY** | `adolfousier/opencrabs` | runtime behaviour, channels, providers, TUI, memory, tools |
| **FACTORY** | `leshchenko1979/opencrabs-dev-factory` | tooling, CI, release automation, process |
| **FORK** (historical) | `leshchenko1979/opencrabs` | **READ-ONLY for new issues**; PRs still land here |

`Closes #N` is now **VALID same-repo**, **FORBIDDEN across trackers**.
Claiming = assignment on the tracker, **BEST-EFFORT: attempted, never assumed**.
Our account is **pull-only on the BINARY tracker** (`adolfousier/opencrabs`:
`push`/`triage`/`maintain`/`admin` all false — the assignment write is
structurally impossible there) and **admin on the FACTORY tracker**. Where the
platform denies the assignment, **record the denial** and let the ledger `claim`
row + `Issue-Ref` trailer **BE** the claim — a **silent skip is a violation**,
because it is indistinguishable from a permission limit. A mandatory duplicate
sweep (open+closed, issues+PRs) runs BEFORE filing.

In the BINARY row, **`tools` means `src/brain/tools/**`** — the runtime tool
registry compiled into the binary — **not** the CLI `tools/**` directory this
document is about. `oc-issue-scope` already encodes exactly this split:
`tools/**` = IN (factory), `src/brain/tools/**` = OUT (binary).

**Topology, verified 2026-10-03:**

| slug | role | evidence |
|---|---|---|
| `adolfousier/opencrabs` | upstream — BINARY tracker + PR target | PUBLIC, `hasIssuesEnabled: true`; real binary traffic #1863–#1905 (TUI BiDi, Discord, cron, plan tool, `telegram_send`, web search) |
| `leshchenko1979/opencrabs-dev-factory` | FACTORY tracker | PUBLIC, `hasIssuesEnabled: true`; **zero** issues at cut-over (brand new) |
| `leshchenko1979/opencrabs` | historical fork — **READ-ONLY for issues** | PUBLIC, issues still enabled; recent 40 issues are a near-continuous run of `fix(tools):` #727–#765 |

The fork's last 40 issues being **factory tooling** is the routing evidence:
that traffic belongs on the factory tracker now. The fork stays the **CI host
and PR target** — `gh run list -R leshchenko1979/opencrabs` shows live
`PR-lane gates` and `Auto-assign issues` runs on 2026-10-03.

**Why "PRs still land here" is separate from "issues are read-only":** the
fork carries the opencrabs source (the PR-lane builds it), the factory repo
carries `tools/**` and the skill. A `Closes #N` in a fork PR can only close a
fork issue — and no new fork issues exist — so a fix PR names its issue with
the tracker-qualified `Issue-Ref` trailer instead (below).

## The `Issue-Ref` trailer under three trackers

`tools/lib/oc_claims.py` parsed a commit trailer's issue number against ONE
fork slug, so a value naming another repository was skipped outright. With
three live trackers, a lane working a binary issue writes
`Issue-Ref: adolfousier/opencrabs#1901`, and the old predicate read **no
issue** from it.

**Decision:** the tracked set is a **HOME-SLUG SET** of all three:

```python
HOME_REPO_SLUGS = (
    "adolfousier/opencrabs",               # BINARY
    "leshchenko1979/opencrabs-dev-factory", # FACTORY
    "leshchenko1979/opencrabs",             # FORK (historical, still resolves)
)
```

A slug outside the set is **still refused** — that refusal is the #379
protection, and it keeps its discriminating control (a non-tracker slug such
as `acme/widgets#7`).

**Resolution ambiguity is the hazard, and it is real:** the three number
spaces overlap, so a bare `#N` names an issue in whichever tracker happens to
carry it. `sweep-closed-claims` must therefore **not** report a claim CLOSED
on a single-repo hit: a token is CLOSED only when it is closed in **every**
home repo where it exists **and open in none**. Anything else is OPEN. That
keeps a real fix-PR/issue state from being read as a closure that did not
happen, and the ambiguity can only ever resolve toward "still open".

## Per-site decisions (the nine HQ-named sites)

| # | site | refs found | decision | why |
|---|---|---|---|---|
| 1 | `tools/issue/oc-issue-create` | `:40` `FORK_REPO`; `:43` `UPSTREAM_SLUG`; `:68` usage; `:219` stub; `:382`/`:397` `--root upstream:` | **add `--tracker binary\|factory`** (default factory); print the resolved target | the creation-time intake tool — the binary-vs-factory split IS its job; a silent default is what made it target the dead tracker |
| 2 | `tools/issue/oc-issue-sweep` | `:39` `FORK`/`UPSTREAM`; `:13` usage; `:87-89` shim; `:96`/`:98` assertions | **add `--factory`**; search all three, open+closed | it IS the mandatory duplicate-sweep tool; a sweep that misses the factory tracker cannot satisfy the law |
| 3 | `tools/issue/oc-issue-scope` | `:105` `FORK_REPO`; `:288`/`:292` `-R "$REPO"` | **default → factory tracker** | body-surface classifier over a *population* of issues; the population is the factory's own work units |
| 4 | `tools/issue/oc-issue-dispatch` | `:616` list; `:651` view; `:840` landed-filter; `:1277` envelope; `:1836` msg; `:1966`/`:2686` fixtures | **add `--tracker binary\|factory`** (default factory) | the issue-reader; envelope URL and list/view slug must follow the tracker |
| 5 | `tools/state/oc-questions` | `:50` `FORK_REPO`; `:503` probe | **default → factory tracker** | files factory questions; the tracker is already framed as a factory parameter (`OC_QUESTIONS_TRACKER` env kept) |
| 6 | `tools/lib/oc_claims.py` | `:266` `FORK_REPO_SLUG`; `:294` `_is_foreign_ref`; `:579` `parse_issue_ref_value` | **home-slug SET of three** (not a filing target — a namespace discriminator) | with three trackers the "our space" set is all three; an upstream ref must now anchor, a foreign slug must still be refused |
| 7 | `tools/state/oc-ledger` | `:4016` confirm view; `:4189` sweep probe; `:4240`/`:4244` texts; `:504` stale name comment | **probe all three**; fail-safe closure; fix the stale name | closure resolution must see the tracker the claim was filed on |
| 8 | `tools/audit/oc-watcher-audit` | `:266/:428/:456/:502` fixtures; `:704`/`:831` fallbacks | **NO CHANGE** | those refs are **CI-run** refs, not issue-tracker refs: the fork still runs `PR-lane gates`; the two fallbacks fire only when a checkpoint names no repo. Verified with `gh run list -R leshchenko1979/opencrabs` on 2026-10-03 |
| 9 | `tools/state/tools.toml.example` | `:16` `opencrabs-skill` paths | **rename → `opencrabs-dev-factory`** | stale repo NAME after the rename; the file would point a new install at a dead path |

**Sites deliberately NOT changed:** `oc-issue-dispatch:3136` `--repo` is a
**PATH to the opencrabs checkout**, not a slug — rewriting it to a slug would
break the tool. It is untouched.

## Verification

- per-tool `--selftest` for every edited tool, and the #379 refusal leg's
  control re-armed with a discriminating non-tracker slug;
- `bash tools/tests/run.sh` (battery) — must exit 0 with FAIL 0;
- `tools/docs/RC-CONTRACT.md` gains a routing stanza on each edited row;
- the tracker permissions that make the assignment leg best-effort are read
  live, never assumed — `gh api repos/<slug> --jq .permissions`: BINARY
  `{pull:true, push:false, triage:false, maintain:false, admin:false}`,
  FACTORY `{admin:true, maintain:true, push:true, triage:true}` (verified
  2026-10-04; mirrors HQ's `SKILL.md:418` commit `7bab7b61`).
