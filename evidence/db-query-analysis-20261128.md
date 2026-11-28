# Database query analysis — ops profile store

**Date:** 2026-11-28 · **Lane:** Editor (database focus) · **Target:** `~/.opencrabs/profiles/ops/opencrabs.db`

## Headline

**The logs cannot answer "which query took longest" — there is no query timing in the binary at all.**
The DB layer is `rusqlite 0.40` with **zero** timing hooks (`grep` for `slow_query|query_took|elapsed_ms`
finds 4 hits, none of them SQL). The `elapsed=NNNs` lines in today's log are background-task
durations (`background_tasks.rs:2035`), not query times — reading them as SQL timings is the
obvious trap.

So the slow statements were identified from the **source call sites** and then **measured directly**
against the live store (read-only, WAL, warm page cache).

## The store

| Property | Value |
|---|---|
| File size | 1.26 GiB (330,080 pages × 4096 B) |
| WAL | 65 MiB |
| journal_mode / synchronous | `wal` / `NORMAL` |
| cache_size (app) | 64 MiB per connection (`database.rs:334`) — healthy, not the problem |
| auto_vacuum | INCREMENTAL |

## Measured timings

| Query | Cold | Warm | Plan |
|---|---:|---:|---|
| `session_search` phrase arm, **unscoped** | **13,009 ms** | 30 ms | `SCAN messages USING idx_created_at` |
| `session_search` phrase arm, **session-scoped** | 0.2 ms | — | `SEARCH messages USING idx_session_id` |
| `usage_ledger` GROUP BY provider (filtered) | **4,687 ms** | — | `SCAN usage_ledger` + temp B-tree |
| `usage_ledger` recent 100 by `created_at` | **445 ms** | — | `SCAN` + temp B-tree |
| `feedback_ledger` `count(*)` | **20,043 ms** | — | covering-index scan of 1.03M rows |
| `messages` `count(*)` | 126 ms | — | index scan |
| `tool_executions` `count(*)` | 961 ms | — | index scan |
| full `messages.content` scan (SUM of lengths) | **>200 s, timed out** | — | table scan |

Cold/warm matters: the 13 s figure is a genuine cold-page-cache read, reproducible on a fresh
connection after eviction. Warm it is 30 ms — which is exactly why the bug hides: it looks fine
until the cache turns over.

## Row populations

| Table | Rows | Notes |
|---|---:|---|
| `feedback_ledger` | 1,031,375 | 90 % `tool_success`; ~225 MB raw payload |
| `tool_executions` | 223,548 | |
| `channel_messages` | 46,267 | **no prune path in source** |
| `messages` | 42,550 | content-bound, not row-bound |
| `usage_ledger` | 41,133 | **no indexes, no prune path** |
| `recent_paths` | 34,053 | |
| `cron_job_runs` | 10,052 | |
| `lost_and_found` | 6,816 | **no indexes** |

## Four defects, ranked by cost

### 1. `usage_ledger` has no indexes at all
`sqlite_master` shows zero index objects on the table. Every aggregate is a full scan with a temp
B-tree: 4.7 s for a per-provider summary, 445 ms for the last 100 rows. Any UI panel that renders
usage pays this on every open.

Compounding it: **no prune path exists.** `grep "DELETE FROM usage_ledger" src/` returns nothing,
while `feedback_ledger` and `messages` both have retention sweeps. 12,802 of 41,133 rows (31 %)
are older than 90 days, against a 90-day retention setting that this table never inherited.

**Fix:** `CREATE INDEX idx_usage_ledger_created ON usage_ledger(created_at)` and
`idx_usage_ledger_session ON usage_ledger(session_id)`; add a retention leg alongside the existing
ones in `services/maintenance.rs`.

### 2. `session_search` unscoped is a full table scan with `LIKE '%term%'` — #855
`contiguous_rows()` (`src/db/repository/message.rs:950`) and `tokenized_rows()` (`:999`) both do
`WHERE content LIKE '%…%' ORDER BY created_at DESC LIMIT ?`. No index can serve a leading-wildcard
LIKE, so SQLite walks `idx_messages_created_at` and reads every row's content until the cap fills —
13 s cold. The `ORDER BY created_at DESC` is why it degrades rather than failing outright.

There is **no FTS table in the store** (`sqlite_master` has zero `%fts%` entries).

**Fix:** an FTS5 virtual table over `messages.content` with insert/update/delete triggers, used as
the first arm with the existing LIKE path kept as fallback for short queries. That is the real fix
for #855 and it turns 13 s into single-digit ms. The session-scoped path is already fast (0.2 ms) —
scoping is the cheap mitigation available today.

### 3. `feedback_ledger` is 90 % success rows
1.03M rows, 900,838 of them `tool_success`. Retention works (90 d, hundreds pruned per sweep — the
log confirms it), but at the current ~12.6k rows/day the 90-day equilibrium is ~1.13M rows, i.e.
**the table is already at its steady state** and will not shrink under the current policy.

`count(*)` on it costs 20 s because even the covering-index scan touches 1.03M entries.

**Fix:** differentiate retention by `event_type` — keep `tool_failure`, `user_correction`,
`provider_error`, `context_compaction` indefinitely (they are the RSI signal), and bound
`tool_success` to a short window (7 d) or sample it. That removes ~87 % of the table without
touching anything the self-improvement loop reads.

### 4. `messages.content` is the real size driver
A `SUM(LENGTH(content))` over 42,550 rows did not finish in 200 s. Only 42k rows producing a
1.26 GiB database means a long tail of very large content blobs (tool outputs, compaction windows).
This is why defect 2 is so expensive: the scan is bandwidth-bound on content, not on row count.

**Fix:** this is the one to measure before acting — the payload distribution (p50/p95/max per
`role`) has to be read first, since a truncation or spill policy for oversized tool-result rows
would change what search can find.

## What I did NOT verify

- The orphan count for `tool_executions` (rows whose `message_id` no longer exists) — the query
  timed out under concurrent writes and is not reported here.
- Per-object space attribution (`dbstat`) — full-file scan, timed out; the 1.26 GiB figure is from
  `page_count × page_size`, which is authoritative.
- Whether the 13 s cold path reproduces on a quiet box; all measurements were taken while the
  daemon was live and writing.

## Recommended order

1. **`usage_ledger` indexes + retention** — smallest change, removes a 4.7 s scan, no semantic risk.
2. **`feedback_ledger` per-event retention** — removes ~900k rows, no RSI signal lost.
3. **FTS5 for `messages`** — the real fix for #855; larger change, needs a migration and backfill.
4. **`messages.content` payload policy** — measure the distribution first.

Steps 1 and 2 are safe to do together. Step 3 wants its own branch and CI gate.
