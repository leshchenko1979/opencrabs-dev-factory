# TRACKER ROUTING — which GitHub repo each `tools/**` site targets

**Owns:** the per-site tracker decision for the **two-stream** issue-routing law
(`SKILL.md` §Hard rules — ISSUE ROUTING; owner order **2026-10-09**, superseding the
2026-10-03 21:17Z three-stream law and its 2026-10-08 14:59Z fork-only re-scope).
Records WHAT each tool targets and WHY, so a later reader does not have to re-derive it.

**Law (verbatim, SKILL.md §Hard rules — ISSUE ROUTING):**

| stream | tracker | what belongs there |
|---|---|---|
| **BINARY** | `leshchenko1979/opencrabs` (the FORK) | runtime behaviour, channels, providers, TUI, memory, tools — **EVERY** opencrabs binary issue |
| **FACTORY** | `leshchenko1979/opencrabs-dev-factory` | tooling, CI, release automation, process |
| **UPSTREAM** | `opencrabs/opencrabs` | **PULL REQUESTS ONLY** — never an issue home (owner order 2026-10-09) |

**The discriminator is RETIRED.** The 2026-10-08 fork-only stream and its
discriminator (the boundary register
[#761](https://github.com/leshchenko1979/opencrabs/issues/761) — `harvest-registry.json`
→ `manual_records`, the `not-upstreamable` rows — and the census `FORK_ONLY_SURFACE`
predicate, `tools/harvest/oc-harvest-census`) no longer route anything: with EVERY
binary issue on the fork there is nothing left to discriminate. The register survives,
if at all, as an informational record.

**RENAME (2026-10-04):** upstream `adolfousier/opencrabs` was renamed to
**`opencrabs/opencrabs`**. The NEW slug is canonical in every site below; the
LEGACY slug still resolves (GitHub redirects it) and is retained **in the
claim-ownership SET only** — so an `Issue-Ref` written before the rename keeps
anchoring — but it is **NOT** a second tracker and NOT a second number space.

`Closes #N` is **VALID same-repo** (a fork binary issue, closed by the fork commit that
fixes it), **FORBIDDEN across trackers** (a fork or factory issue has no upstream number
space; the upstream PR body ends `Original issue: <full URL>`). Claiming = assignment on
the tracker, **ATTEMPTED AND VERIFIED**. A denied assignment is **recorded, never silently
skipped**; the ledger `claim` row + `Issue-Ref` trailer then carry the claim. A mandatory
duplicate sweep (open+closed, issues+PRs) runs BEFORE filing.

## The assignment leg — VERIFIED on both live trackers

**Owner order 2026-10-03:** claiming is the tracker ASSIGNMENT (the public
signal) **plus** the internal `Issue-Ref` trailer + workers-ledger `claim` row.

- **BINARY tracker — the FORK `leshchenko1979/opencrabs`:** we hold `admin`, so the
  assignment WRITE succeeds (`gh issue edit <N> --add-assignee @me` → rc 0).
- **FACTORY tracker `leshchenko1979/opencrabs-dev-factory`:** we hold `admin`; the
  assignment has always worked.
- **The upstream TRIAGE grant (2026-10-04) is now HISTORICAL** — `opencrabs/opencrabs`
  receives PRs only, so no issue claim happens there.
- **Where a platform STILL denies the assignment**, **record the denial** and let the
  ledger `claim` row + `Issue-Ref` trailer **BE** the claim. A **silent skip is a
  violation** — it is indistinguishable from a permission limit.

In the BINARY row, **`tools` means `src/brain/tools/**`** — the runtime tool
registry compiled into the binary — **not** the CLI `tools/**` directory this
document is about. `oc-issue-scope` already encodes exactly this split:
`tools/**` = IN (factory), `src/brain/tools/**` = OUT (binary).

**Topology, verified live:**

| slug | role | evidence |
|---|---|---|
| `leshchenko1979/opencrabs` | **BINARY tracker** + CI host + PR target | PUBLIC, issues enabled; we hold `admin` |
| `leshchenko1979/opencrabs-dev-factory` | FACTORY tracker | PUBLIC, issues enabled; we hold `admin` |
| `opencrabs/opencrabs` | **PR target ONLY** — never an issue home | PUBLIC, `hasIssuesEnabled: true` (legacy issues readable); renamed from `adolfousier/opencrabs` |
| `adolfousier/opencrabs` | **legacy alias** of the row above (GitHub redirects it) | retained in the claim-ownership set only; not a separate number space |

**Why "PRs still land" upstream is separate from the issue streams:** the fork carries
the opencrabs source (the PR-lane builds it); the HARVEST lane ports mature fork work
upstream as PULL REQUESTS. A `Closes #N` in a **fork** PR closes a **fork** issue. The
upstream PR body carries `Original issue: <fork issue URL>`, never `Closes #N`.

## The `Issue-Ref` trailer under two trackers

`tools/lib/oc_claims.py` parses a commit trailer's issue number against a
**HOME-SLUG SET** — every tracker the fleet files on, plus the legacy slugs so
pre-rename refs still anchor:

```python
HOME_REPO_SLUGS = (
    "leshchenko1979/opencrabs",             # BINARY (the fork — canonical since 2026-10-09)
    "leshchenko1979/opencrabs-dev-factory", # FACTORY
    "opencrabs/opencrabs",                  # UPSTREAM (PR-side refs + legacy issue refs)
    "adolfousier/opencrabs",                # UPSTREAM legacy slug (redirects)
)
```

A slug outside the set is **still refused** — that refusal is the #379
protection, and it keeps its discriminating control (a non-tracker slug such
as `acme/widgets#7`).

**Resolution ambiguity is the hazard, and it is real:** the number spaces overlap, so a
bare `#N` names an issue in whichever tracker happens to carry it. `sweep-closed-claims`
must therefore **not** report a claim CLOSED on a single-repo hit: a token is CLOSED only
when it is closed in **every** home repo where it exists **and open in none**. Anything
else is OPEN — the ambiguity can only ever resolve toward "still open".

## Per-site decisions (the HQ-named sites)

| # | site | refs found | decision | why |
|---|---|---|---|---|
| 1 | `tools/issue/oc-issue-create` | `:43` `FORK_REPO`; `:56` `UPSTREAM_SLUG`; usage; `--root upstream:` normaliser | **`--tracker binary\|factory`** (default factory); `binary` resolves to the FORK; legacy `fork` accepted as an alias of `binary`; print the resolved target; `--root` strips the upstream slugs | the creation-time intake tool — the stream split IS its job; `binary` now lands on the fork |
| 2 | `tools/issue/oc-issue-sweep` | `:48` `UPSTREAM`; usage; shim; assertions | **`--factory`**; search fork + factory open+closed, plus upstream closed for uniqueness | it IS the mandatory duplicate-sweep tool; a sweep that misses a live tracker cannot satisfy the law |
| 3 | `tools/issue/oc-issue-scope` | `FORK_REPO`; `-R "$REPO"` | **default → the FORK** | body-surface classifier over a *population* of issues; the binary population now lives on the fork |
| 4 | `tools/issue/oc-issue-dispatch` | list/view/landed-filter/envelope/fixtures; `TRACKERS["binary"]` | **`--tracker binary\|factory`** (default factory); `binary` → fork | the issue-reader; envelope URL and list/view slug must follow the tracker |
| 5 | `tools/state/oc-questions` | `FORK_REPO`; probe | **default → factory tracker** | files factory questions; the tracker is already framed as a factory parameter (`OC_QUESTIONS_TRACKER` env kept) |
| 6 | `tools/lib/oc_claims.py` | `HOME_REPO_SLUGS`; `_is_foreign_ref`; `parse_issue_ref_value` | **home-slug SET** (fork + factory + upstream + legacy) | with two live trackers + a PR-only upstream, "our space" is the union; an upstream ref must anchor, a foreign slug must still be refused |
| 7 | `tools/state/oc-ledger` | `HOME_REPOS`; confirm view; sweep probe; texts | **probe fork + factory (+ upstream for legacy)**; fail-safe closure | closure resolution must see the tracker the claim was filed on |
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
- `oc-vendor-drift` reads `IN_SYNC` — a reworded routing comment inside a vendored tool
  must move `vendor-manifest.json`'s `match`/`match_upstream` pair with it, or the drift
  audit reads the rewording as drift;
- the tracker permissions that gate the assignment leg are read live, never
  assumed — `gh api repos/<slug> --jq .permissions`.
