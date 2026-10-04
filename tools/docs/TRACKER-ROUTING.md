# TRACKER ROUTING — which GitHub repo each `tools/**` site targets

**Owns:** the per-site tracker decision for the two-stream issue-routing law
(SKILL.md, v0.4.284, owner order 2026-10-03 21:17Z). Records WHAT each tool
targets and WHY, so a later reader does not have to re-derive it.

**Law (verbatim, SKILL.md):**

| stream | tracker | what belongs there |
|---|---|---|
| **BINARY** | `opencrabs/opencrabs` | runtime behaviour, channels, providers, TUI, memory, tools |
| **FACTORY** | `leshchenko1979/opencrabs-dev-factory` | tooling, CI, release automation, process |
| **FORK** (historical) | `leshchenko1979/opencrabs` | **READ-ONLY for new issues**; PRs still land here |

**RENAME (2026-10-04):** upstream `adolfousier/opencrabs` was renamed to
**`opencrabs/opencrabs`**. The NEW slug is canonical in every site below; the
LEGACY slug still resolves (GitHub redirects it) and is retained **in the
claim-ownership SET only** — so an `Issue-Ref` written before the rename keeps
anchoring — but it is **NOT** a second tracker and NOT a second number space.

`Closes #N` is now **VALID same-repo**, **FORBIDDEN across trackers**.
Claiming = assignment on the tracker, **ATTEMPTED AND VERIFIED** (owner order
2026-10-03; the binary-tracker leg became verifiable once TRIAGE was granted —
see below). A denied assignment is **recorded, never silently skipped**; the
ledger `claim` row + `Issue-Ref` trailer then carry the claim. A mandatory
duplicate sweep (open+closed, issues+PRs) runs BEFORE filing.

## The assignment leg — VERIFIED, with a recorded denial path

**Owner order 2026-10-03:** claiming is the tracker ASSIGNMENT (the public
signal) **plus** the internal `Issue-Ref` trailer + workers-ledger `claim` row.

- **BINARY tracker (`opencrabs/opencrabs`):** our account now holds **TRIAGE**,
  so the assignment WRITE succeeds — `gh issue edit <N> --add-assignee @me` →
  rc 0, read back `['leshchenko1979']` (verified 2026-10-04; HQ ledger n=14388,
  q57 granted). Permissions read live:
  `{pull:true, triage:true, push:false, maintain:false, admin:false}`.
- **FACTORY tracker:** we hold `admin`; the assignment has always worked.
- **Where the platform STILL denies the assignment** (a repo where we hold no
  write-capable role), **record the denial** and let the ledger `claim` row +
  `Issue-Ref` trailer **BE** the claim. A **silent skip is a violation** — it is
  indistinguishable from a permission limit.

In the BINARY row, **`tools` means `src/brain/tools/**`** — the runtime tool
registry compiled into the binary — **not** the CLI `tools/**` directory this
document is about. `oc-issue-scope` already encodes exactly this split:
`tools/**` = IN (factory), `src/brain/tools/**` = OUT (binary).

**Topology, verified 2026-10-04:**

| slug | role | evidence |
|---|---|---|
| `opencrabs/opencrabs` | upstream — BINARY tracker + PR target | PUBLIC, `hasIssuesEnabled: true`; **TRIAGE** held; renamed from `adolfousier/opencrabs` |
| `adolfousier/opencrabs` | **legacy alias** of the row above (GitHub redirects it) | retained in the claim-ownership set only; not a separate number space |
| `leshchenko1979/opencrabs-dev-factory` | FACTORY tracker | PUBLIC, `hasIssuesEnabled: true`; we hold `admin` |
| `leshchenko1979/opencrabs` | historical fork — **READ-ONLY for issues** | PUBLIC, issues still enabled; the CI host and PR target |

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
`Issue-Ref: opencrabs/opencrabs#1901` (or the legacy `adolfousier/opencrabs#1901`),
and the old one-slug predicate read **no issue** from it.

**Decision:** the tracked set is a **HOME-SLUG SET** — every tracker the fleet
files on, PLUS the binary tracker's legacy slug so pre-rename refs still anchor:

```python
HOME_REPO_SLUGS = (
    "opencrabs/opencrabs",                  # BINARY (canonical)
    "adolfousier/opencrabs",                # BINARY (legacy slug; redirects)
    "leshchenko1979/opencrabs-dev-factory", # FACTORY
    "leshchenko1979/opencrabs",             # FORK (historical, still resolves)
)
```

A slug outside the set is **still refused** — that refusal is the #379
protection, and it keeps its discriminating control (a non-tracker slug such
as `acme/widgets#7`). Dropping the legacy slug would turn every pre-rename
binary-tracker ref into a #379 refusal, so it stays.

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
| 1 | `tools/issue/oc-issue-create` | `:43` `FORK_REPO`; `:56` `UPSTREAM_SLUG`; usage; `--root upstream:` normaliser | **`--tracker binary\|factory`** (default factory); print the resolved target; `--root` strips BOTH binary slugs | the creation-time intake tool — the binary-vs-factory split IS its job; a silent default is what made it target the dead tracker |
| 2 | `tools/issue/oc-issue-sweep` | `:48` `UPSTREAM`; usage; shim; assertions | **`--factory`**; search all three, open+closed | it IS the mandatory duplicate-sweep tool; a sweep that misses the factory tracker cannot satisfy the law |
| 3 | `tools/issue/oc-issue-scope` | `FORK_REPO`; `-R "$REPO"` | **default → factory tracker** | body-surface classifier over a *population* of issues; the population is the factory's own work units |
| 4 | `tools/issue/oc-issue-dispatch` | list/view/landed-filter/envelope/fixtures; `TRACKERS["binary"]` | **`--tracker binary\|factory`** (default factory) | the issue-reader; envelope URL and list/view slug must follow the tracker |
| 5 | `tools/state/oc-questions` | `FORK_REPO`; probe | **default → factory tracker** | files factory questions; the tracker is already framed as a factory parameter (`OC_QUESTIONS_TRACKER` env kept) |
| 6 | `tools/lib/oc_claims.py` | `HOME_REPO_SLUGS`; `_is_foreign_ref`; `parse_issue_ref_value` | **home-slug SET** (4 entries incl. the binary legacy slug) | with three trackers the "our space" set is all of them; an upstream ref must anchor, a foreign slug must still be refused |
| 7 | `tools/state/oc-ledger` | `HOME_REPOS`; confirm view; sweep probe; texts | **probe all three**; fail-safe closure; fix the stale name | closure resolution must see the tracker the claim was filed on |
| 8 | `tools/audit/oc-watcher-audit` | fixtures; fallbacks | **NO CHANGE** | those refs are **CI-run** refs, not issue-tracker refs: the fork still runs `PR-lane gates`; the two fallbacks fire only when a checkpoint names no repo |
| 9 | `tools/state/tools.toml.example` | `opencrabs-skill` paths | **rename → `opencrabs-dev-factory`** | stale repo NAME after the rename; the file would point a new install at a dead path |

**Sites deliberately NOT changed:** `oc-issue-dispatch:3136` `--repo` is a
**PATH to the opencrabs checkout**, not a slug — rewriting it to a slug would
break the tool. It is untouched.

## Verification

- per-tool `--selftest` for every edited tool, and the #379 refusal leg's
  control re-armed with a discriminating non-tracker slug;
- `bash tools/tests/run.sh` (battery) — must exit 0 with FAIL 0;
- `tools/docs/RC-CONTRACT.md` gains a routing stanza on each edited row;
- the tracker permissions that gate the assignment leg are read live, never
  assumed — `gh api repos/<slug> --jq .permissions`: BINARY
  `{pull:true, triage:true, push:false, maintain:false, admin:false}`,
  FACTORY `{admin:true, maintain:true, push:true, triage:true}` (verified
  2026-10-04; mirrors HQ's `SKILL.md:418` commit `7bab7b61`).
