# HEALTH-CLASSES.md — 8-Class Rotating System Health & Cleanliness Architecture

**Owner order 2026-09-11.** Toolsmith owns the cleanup/health process.
This document defines the 8-class rotating system object health catalog,
mechanized by `tools/state/oc-health`.

---

## 1. Architecture: Base Invariants vs. Rotating Classes

A monolithic sweep inspecting every fleet subsystem every hour creates
unnecessary I/O pressure and API churn. The 8-class rotation divides checks
into two tiers:

1. **Base Invariants (Every Run):**
   Fast, critical measurements executed on every invocation:
   - Root filesystem headroom (`df -P /` warn at 85%, urgent at 89%)
   - Critical deadlock locks (`fanout.*.lock`, legacy `fanout.lock.*`, `run/wave-*.lock` >24h with dead owner PID)
   - Snapshot mirror and stale `/tmp/oc-*` cleanup (when `--reap` is passed)

2. **Rotating Class (1 Class per Hourly Run or `--class <name>`):**
   One class from the 8-class ring is selected per run (advancing round-robin
   in `health-rotation.json`). A full deep audit across all 8 classes completes
   every 8 hours. Running `oc-health --all` or `oc-health --class all` executes
   all 8 classes in a single pass.

---

## 2. The 8 System Object Classes

```
                   ┌──────────────────────────────────┐
                   │    Base Critical Invariants      │
                   │ (Disk Headroom / Deadlock Locks) │
                   └────────────────┬─────────────────┘
                                    │
    ┌───────────────┬───────────────┼───────────────┬───────────────┐
    ▼               ▼               ▼               ▼               ▼
1. filesystem  2. runtime_procs 3. persistence    4. git_vcs   5. schedulers
    │                                                               │
    └───────────────┬───────────────────────────────┬───────────────┘
                    ▼                               ▼
              6. fleet_lanes                     7. logs
                    │
                    ▼
            8. issue_portfolio
```

### Class 1: `filesystem`
- **Objects Audited:** `/tmp`, `$OC_DEV_STATE`, worktrees, logs.
- **Invariants Checked:**
  - Inode usage and disk headroom (`df -P /`).
  - Stale fanout/wave locks (`fanout.*.lock`, legacy `fanout.lock.*`, `run/wave-*.lock`, `run/wave-*.sent`).
  - Stale temporary scratch directories (`/tmp/oc-*` >48h) and dead PID snapshot mirrors (`oc-snap-*-<pid>`).
  - State directory bloat (`$OC_DEV_STATE` >200MB).
- **Remediation:** Under `--reap`, prune dead locks, dead mirrors, and tmp >48h.

### Class 2: `runtime_procs`
- **Objects Audited:** Live processes, detached jobs (`tmp/detached/*.json`), background watchers.
- **Window:** `OC_HEALTH_WATCHER_WINDOW_H` — rolling audit window in hours (default 24, `0` = all history).
- **Invariants Checked:**
  - `gh run watch` with no `--interval` (forbidden 3s default) → `UNTHROTTLED_WATCH`.
  - `gh run watch` at an interval other than 30/60 → `OFF_SPEC_INTERVAL`.
  - Banned `nohup` subshell launches → `NOHUP_SPAWN`.
  - Handrolled sleep/polling loops → `HANDROLLED_SLEEP_LOOP`.
  - Zombie/orphan background worker processes.
- **Count semantics:** the finding reports the real violation count, a per-type breakdown, and how many are still `Running`; an unparseable audit payload is a measurement failure (rc 3), never a fabricated count.
- **Remediation:** Report via `WARN`; notify owning lanes if processes are orphaned.

### Class 3: `persistence`
- **Objects Audited:** `opencrabs.db`, `workers-ledger.json`, backup artifacts, generated sidecars.
- **Invariants Checked:**
  - Session SQLite DB size (>1GB).
  - Ledger backup retention (keep 3 newest; never delete <24h).
  - Ledger JSON schema integrity and JSON syntax validity.
  - Backup file bloat and corruption markers (`*.corrupt-*.bak`).
  - **3b `sidecar-retention` — SAFE:** generated `*.bak` / `*.bak-*` sidecars in the state dir; keep newest N **per source**, prune beyond that only past the age floor; sources not tracked in the state repo are reported and never reaped.
- **Remediation:** Under `--reap`, prune ledger backups beyond keep count and sidecars beyond their per-source keep-window and age floor. Sidecar retention is a separate check from ledger-backup retention: the former is per source, the latter global; ledger backups are excluded by prefix so neither check double-counts them. `OC_HEALTH_SIDECAR_KEEP` and `OC_HEALTH_SIDECAR_MAX_AGE_H` tune the sidecar check.

### Class 4: `git_vcs`
- **Objects Audited:** Skill repo (`opencrabs-dev`), fork repo (`~/opencrabs`), worktree directories.
- **Invariants Checked:**
  - Orphaned / unregistered worktree directories on disk (`/root/oc-work/*`, `/root/oc-wt-*` vs `git worktree list`).
  - Shared skill checkout cleanliness (`git status --porcelain`).
  - Remote tracking divergence (`HEAD` vs `origin/main`).
  - Version/ledger consistency (`oc-ledger check-version`).
  - Unstaged tracked-file deletion inside a registered worktree (porcelain ` D` — check 18).
- **Remediation:** Report only. Worktree removal must use `oc-wt remove` (dirty-tree safety gate).

### Class 5: `schedulers`
- **Objects Audited:** `cron_jobs` table in `opencrabs.db`.
- **Invariants Checked:**
  - Law-carrying dev crons enabled (`oc-harvest-dispatch-4h`, `oc-roster-detached-sweep`, `oc-health-hourly`, `oc-upstream-delta-watch`).
    - **NAME CORRECTION (2026-09-19):** the harvest patrol was listed as `harvest-watch-4h` until this date. **No such job has ever existed in `cron_jobs`** — the live name is `oc-harvest-dispatch-4h` (id `73158e43-3b04-4464-bf82-8d9065a191bb`; the `harvest-watch-4h` spelling is the v0.4.203 correction, the live row predates it). A query matching the stale name can never fire on the real job, so the check was blind to the harvest patrol's state for its whole life. **FIXED in `tools/state/oc-health` class 5 (Toolsmith, issue #339, 2026-09-19).** The query no longer names jobs: it matches a **stem** per patrol (`_LAWCARRY` — `oc-harvest-dispatch%`, `oc-roster-detached-sweep%`, `oc-health-hourly%`, `oc-upstream-delta-watch%`), so a rename under the cron-cadence law cannot blind the check again. Two further defects were found and fixed in the same pass: `oc-upstream-delta-watch` was **absent from the list entirely** (a fourth law-carrying patrol, never audited), and the direction was hardcoded to "disabled = finding" with no awareness of the owner order below. The check now reads `$STATE/pacemakers-off` and **inverts**: with the marker present it flags `cron-enabled-against-order` for a patrol that is ENABLED, and reports clean (`crons: pacemakers-off order honoured, zero DM leaks`) when all four are off as ordered. Selftest legs `schedulers-lawcron` (the exact #339 regression), `schedulers-rename-proof`, `schedulers-against-order` and `schedulers-offorder-*` cover both directions; all four redden under mutation.
    - **OWNER-ORDERED OFF (2026-09-18 20:53Z, still standing):** the owner ordered every ops-profile pacemaker switched off (*"Turn off all of your pacemakers for now"*). Executed and read back the same evening: **11 ops-owned crons, 0 enabled** — all four above included. **A disabled state is therefore the EXPECTED reading, not a finding, for as long as that order stands.** A class-5 report flagging these crons as "disabled" is re-reporting the owner's own order back to him; treat it as a stale invariant, not a discovery. **MARKER LIFECYCLE (2026-09-19):** the `<state dir>/pacemakers-off` marker this check reads MUST exist for as long as the order stands and MUST be removed the moment the owner lifts it -- an absent marker flips the check back to the stale direction and it re-reports the order as a finding on every run (measured 2026-09-19: `oc-health --class schedulers` -> `8 QUIRK cron-disabled`). The invariant's live purpose inverts until he lifts it: it must fail loudly if one of these crons is **enabled** against the order, and resume flagging disabled ones only after the order is lifted.
  - Dev cron delivery routing: zero leaks to private DMs (positive Telegram chat ID or hardcoded owner ID).
  - Blank `deliver_to` allowed when cron delivers internally via `session_notify`.
- **Remediation:** Flag via `QUIRK` — `cron-disabled` (order NOT standing) or `cron-enabled-against-order` (order standing), plus DM leaks.

### Class 6: `fleet_lanes`
- **Objects Audited:** Roster records in `workers-ledger.json`, active session bindings.
- **Invariants Checked:**
  - Roster integrity: valid JSON, duplicate session UUIDs, missing role tags.
  - Dead session IDs registered as active/live workers.
  - Unclaimed/orphaned work claims or unclosed task markers.
- **Remediation:** Report via `REPORT` / `QUIRK`; update roster via `oc-ledger roster-retire` if authorized.

### Class 7: `logs`
- **Objects Audited:** `$OC_DEV_STATE/tools.log`, `opencrabs.YYYY-MM-DD`, channel attachments.
- **Invariants Checked:**
  - `tools.log` JSONL syntax integrity (0 malformed lines; name historical non-JSON lines without modifying evidence).
  - Anomaly spikes in daemon log (recurring `ERROR` or malformed skill frontmatter warnings).
  - Tool execution failure rate: flag any `oc-*` tool with >15% non-zero exit rate in the last 24h.
  - Execution jitter: flag tool invocations taking >10s (e.g. heavy worktree scans).
- **Remediation:** Report only. Never delete or rewrite log evidence.

### Class 8: `issue_portfolio`
- **Objects Audited:** Fork issues (`leshchenko1979/opencrabs`), upstream issues (`opencrabs/opencrabs`), ledger issue claims.
- **Invariants Checked:**
  - Unassigned open issues on the fork lacking a worker claim in `workers-ledger.json`.
  - Stale / abandoned claims: issues claimed in ledger where lane has had 0 commits >48h.
  - Ghost claims: issues closed on GitHub but still listed as active claims in ledger.
  - Branch linkage drift: claimed issue branch deleted from git remotes.
- **Remediation:** Report via `REPORT` / `QUIRK` for Triage/HQ assignment.

---

## 3. Rotation State Schema (`health-rotation.json`)

Location: `$STATE/health-rotation.json` (overridden by `OC_HEALTH_ROTATION_FILE`).

```json
{
  "version": 1,
  "current_class": "logs",
  "next_class": "issue_portfolio",
  "last_rotated_at": "2026-09-11T22:00:00Z",
  "cycle_count": 42,
  "history": {
    "filesystem": { "last_run": "2026-09-11T16:00:00Z", "findings": 1, "reaped": 72 },
    "runtime_procs": { "last_run": "2026-09-11T17:00:00Z", "findings": 0, "reaped": 0 },
    "persistence": { "last_run": "2026-09-11T18:00:00Z", "findings": 0, "reaped": 0 },
    "git_vcs": { "last_run": "2026-09-11T19:00:00Z", "findings": 0, "reaped": 0 },
    "schedulers": { "last_run": "2026-09-11T20:00:00Z", "findings": 0, "reaped": 0 },
    "fleet_lanes": { "last_run": "2026-09-11T21:00:00Z", "findings": 0, "reaped": 0 },
    "logs": { "last_run": "2026-09-11T22:00:00Z", "findings": 1, "reaped": 0 },
    "issue_portfolio": { "last_run": "2026-09-11T15:00:00Z", "findings": 0, "reaped": 0 }
  }
}
```

---

## 4. CLI Contract & Flags

```bash
oc-health [--class <name>|--all] [--rotate] [--status] [--reap] [--json] [--quiet] [--selftest]
```

- `--class <name>`: Explicitly execute a specific class (`filesystem`, `runtime_procs`, `persistence`, `git_vcs`, `schedulers`, `fleet_lanes`, `logs`, `issue_portfolio`, or `all`).
- `--all`: Execute all 8 classes in a single pass.
- `--rotate`: (Default when `--class` is omitted) Execute base invariants + the next rotating class, advancing `health-rotation.json`.
- `--status`: Display current rotation state, last execution time per class, and next class up.
- `--reap`: Apply safe remediations (stale locks, backups > keep, dead mirrors, tmp > 48h).
- `--json`: Output machine-readable JSON matching the cron delivery contract.
- `--quiet`: Print only findings, suppressing clean lines.
- `--selftest`: Hermetic offline test suite verifying all 8 classes and rotation engine (27 assertions).

**Environment overrides (hermetic testing / tuning):** `OC_HEALTH_STATE`, `OC_HEALTH_FORK`, `OC_HEALTH_DB`, `OC_HEALTH_TMP_GLOB`, `OC_HEALTH_TMP2_GLOB`, `OC_HEALTH_TMP2_MAX_AGE_H`, `OC_HEALTH_SKILL_DIR`, `OC_HEALTH_WT_PATTERNS`, `OC_HEALTH_SKIP_VERSION`, `OC_HEALTH_LOG`, `OC_HEALTH_ROTATION_FILE`, `OC_HEALTH_DETACHED_DIR`, `OC_HEALTH_WATCHER_WINDOW_H`.

---

## 5. Exit Code Conventions

- `0`: Clean (no findings in active class or base invariants).
- `1`: Findings present (`WARN`, `QUIRK`, `REPORT`, or `URGENT`).
- `2`: CLI usage / argument syntax error.
- `3`: Measurement failure (a required subsystem or check failed to measure).
