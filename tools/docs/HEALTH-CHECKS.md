# HEALTH-CHECKS.md — hourly fleet health & cleanliness

**Owner order 2026-09-11.** Toolsmith owns the cleanup/health process. This file
is the operational runbook and remediation catalog mechanized by `tools/state/oc-health`
(see `tools/docs/HEALTH-CLASSES.md` for the 8-class architecture and CLI contract).

**Primary rule (owner):** *workers clean after themselves.* A lane that leaves
debris behind owns that debris. This process exists to (a) catch mechanical
debris automatically, and (b) **warn** on quirks — not to silently tidy up
after sloppy lanes and hide the pattern.

**Discipline for every check below:**
- **Report first, remediate only the SAFE class.** Safe = provably dead
  (age > threshold AND no live owner). Never delete anything a live lane may
  still hold; never delete evidence (see *Never touch* at the end).
- **Warn, don't silently fix, on the QUIRK class** — a lane leaving debris is a
  process signal; the health check names the lane/object, it does not erase the symptom.
- **Every remediation prints a receipt line** (what, count, bytes freed). A
  cleanup with no receipt is indistinguishable from a no-op.
- **Idempotent:** running twice in succession must be a no-op the second time.

---

## 1. Stale fanout & wave locks — `SAFE` (reap) + `QUIRK` (warn)

- **Where:** `$OC_DEV_STATE/fanout.<runid>.lock` (legacy `fanout.lock.<runid>` still swept), `$OC_DEV_STATE/run/wave-*.lock`
- **Content:** `pid=<n> ts=<ISO> run=<n>`
- **Invariant:** Lock age >24h **and** associated PID dead (`kill -0`), or recorded run completed.
- **Remediation (`--reap`):** Remove stale lock; report `reaped N locks`.
- **Quirk form:** A lock whose PID is active but age >24h $\to$ warn, do not reap.

## 2. Orphaned / unregistered worktrees — `SAFE` (report) + `QUIRK` (warn)

- **Where:** `git -C ~/opencrabs worktree list` vs `/root/oc-wt-*` + `/root/oc-work/*`
- **Invariant:** Count registered worktrees vs directories on disk. Flag directories
  with no registration (crashed `oc-wt remove`) and registered worktrees whose
  branch is already merged into main.
- **Remediation:** Report only. Removal is `tools/git/oc-wt remove <task>` — enforces dirty-tree
  gate and journals deletion; never use raw `rm -rf`.

## 3. Ledger backups — `SAFE` (prune old, keep newest N)

- **Where:** `$OC_DEV_STATE/workers-ledger.json.bak.*`, `*.corrupt-*.bak`, `*.20*.bak`
- **Invariant:** Backups older than 7 days when backup count >3.
- **Remediation (`--reap`):** Keep 3 newest backups, delete older. Never delete a backup
  younger than 24h (crash insurance for active writes).

## 3b. Generated sidecar retention — `SAFE` (prune old, keep newest N per source)

- **Where:** `$OC_DEV_STATE` generated `*.bak` / `*.bak-*` sidecars.
- **Invariant:** Keep the newest `OC_HEALTH_SIDECAR_KEEP` sidecars per source (default `3`); prune only beyond that keep-window and only when older than `OC_HEALTH_SIDECAR_MAX_AGE_H` (default `48` hours). The check uses the writer's filename timestamp where present and falls back to mtime.
- **Source safety:** If the sidecar's **source file is not tracked** in the state repo, report `sidecar-untracked-source` and NEVER reap it — it may be the only copy of that reading.
- **Scope:** This is an allowlist of generated sidecar patterns, never a general state-dir clean; marker files such as `pacemakers-off` cannot become candidates. It is separate from ledger-backup retention: ledger backups keep newest N globally and are excluded by prefix, so the checks cannot double-count them.
- **Remediation (`--reap`):** Run `oc-health --class persistence --reap` to prune beyond the per-source keep-window and age floor. `OC_HEALTH_SIDECAR_KEEP` and `OC_HEALTH_SIDECAR_MAX_AGE_H` tune the check. Reports are emitted without `--reap`; `--reap` adds a receipt naming the pruned count and kept count.

## 4. State-dir bloat — `REPORT`

- **Where:** `$OC_DEV_STATE` total; per-file top 10.
- **Invariant:** Total state-dir size >200 MB, or any single non-essential file >50 MB.
- **Remediation:** Report; rotation of `tools.log` is a Toolsmith decision, not an automatic one.

## 5. Disk headroom — `REPORT` + `URGENT`

- **Where:** Root filesystem (`df -P /`)
- **Invariant:** Headroom $\ge 85\%$ triggers `WARN`; $\ge 89\%$ triggers `URGENT`.
- **Remediation:** At $\ge 89\%$, execute `vds-servers/scripts/cleanup-unified.sh` (per
  AGENTS.md Gatus rule), then re-verify headroom.

## 6. Shared-checkout cleanliness — `QUIRK` (warn, loud)

- **Where:** `/root/.opencrabs/profiles/ops/skills/opencrabs-dev` (shared skill repository).
- **Invariant:** `git status --porcelain` must be clean of unexpected untracked/modified files.
  Remote tracking must satisfy `HEAD == origin/main`.
- **Remediation:** Warn only, naming untracked/modified files.

## 7. Version / ledger consistency — `QUIRK`

- **Where:** `SKILL.md` version vs `workers-ledger.json` metadata.
- **Invariant:** `tools/state/oc-ledger check-version` must report MATCH. Lane `last_acked` must
  not be stale (>7 days).
- **Remediation:** Report. The verdict NAMES its cause (#359) and the remediation follows it:
  **FLEET-LEVEL** (the registry fields lag `SKILL.md` while 0 workers are behind — a skipped
  sync) → `oc-ledger sync` (HQ release flow); **LANE-LEVEL** (≥1 worker's `last_acked.version`
  is behind `SKILL.md`) → those lanes must re-ack (`oc-ledger ack <uuid> <version>`), and a
  fleet sync is the WRONG heal. Both keep rc 1 (`hq.md:109`).

## 8. Cron liveness & routing — `QUIRK` + `SAFE` (re-arm)

- **Where:** OpenCrabs profile cron table (`opencrabs cron list` / DB).
- **Invariant:** Every law-carrying cron has `last_run_at` within $2\times$ its interval
  and `enabled=1`. Delivery target must route to forum chat `-1003936827469` or active session.
- **Remediation:** Re-enable / re-arm; report any silently stopped cron or misrouted delivery.

## 9. Temp accumulation — `SAFE` (prune old)

- **Where:** `/tmp/oc-*`
- **Invariant:** Temporary files/directories older than 48h with no live PID holding them.
- **Remediation (`--reap`):** Delete provably dead files; report count and freed bytes.
  Age check alone is insufficient; live PID verification is mandatory.

## 9b. Leaked `mktemp` WORKDIRs — `SAFE` (prune old)

- **Where:** `/tmp/tmp.*` (`OC_HEALTH_TMP2_GLOB` overrides).
- **Origin (M2-22, 2026-09-12):** `oc-deploy`'s swap path held the downloaded
  ~83 MB release artifact + `state-backup/` in a `mktemp -d` WORKDIR that was
  never removed, and the battery's `run_selftest()` leaked one state dir per
  tool per run. Together they reached **7615 dirs / 3.3 GB** and took the root
  filesystem to **85 %**. Both producers are fixed (the WORKDIR now dies with
  its subshell; `run_selftest()` removes its state dir); this check is the
  backstop so the class cannot silently regrow.
- **Invariant:** A `/tmp/tmp.*` directory is a candidate **only** when it carries
  the oc-deploy WORKDIR signature — `build-flags.txt` **or** `state-backup/` —
  **and** its mtime is older than `OC_HEALTH_TMP2_MAX_AGE_H` (default **24 h**).
  Both gates are mandatory. A generic `mktemp -d` from any other tool lives in
  the same namespace and must never be touched; a *live* swap rewrites its
  WORKDIR continuously, so a signature dir a day old cannot belong to one.
  (The manual emergency reap used a 90-minute gate to protect a chain in
  flight; the standing check is deliberately more conservative.)
- **Remediation (`--reap`):** `rm -rf` candidates; report count. Finding slug
  `stale-tmp2` (check 9) so the count stays attributable and never blends into
  the `/tmp/oc-*` figure.

## 9c. Leaked `mktemp` FILEs — `SAFE` (prune old) / `REPORT` (unknown class)

- **Where:** non-directory `/tmp/tmp.*` (`OC_HEALTH_TMP3_GLOB` overrides).
- **Origin (M2-25, 2026-09-12):** `oc-issue-sweep` wrote three siblings of its
  `mktemp` file — `.raw`, `.sorted`, `.final` — while its EXIT trap removed only
  the base path, so every invocation dripped 3 files into `/tmp`. Measured:
  **1070 files, 0.1 MB, oldest 2 days.** The producer is fixed (`83008e1d` — the
  trap now names all four paths); this check is the backstop so the class cannot
  silently regrow. Sibling of 9b, for the *file* namespace rather than the dir.
- **Invariant:** a file is a reap candidate **only** when its name matches the
  known leak signature — `tmp.*.raw` / `tmp.*.sorted` / `tmp.*.final` — **and**
  its mtime is older than `OC_HEALTH_TMP3_MAX_AGE_H` (default **24 h**). Both
  gates are mandatory: another tool's `mktemp` file shares this namespace, so a
  signature is required before anything is removed.
- **Second branch (`REPORT`, never reaped):** any *other* `/tmp/tmp.*` file past
  the age gate is reported as `stale-tmp3-unknown` — a new leak class shows up
  here instead of hiding behind an unknown suffix. It is deliberately never
  removed: a detector that eats a live temp file is worse than the leak it hunts.
- **Remediation (`--reap`):** `rm -f` the signature-matched candidates only;
  report the count. Finding slugs `stale-tmp3` (check 9) and `stale-tmp3-unknown`,
  so neither count blends into the `/tmp/oc-*` or WORKDIR figures.

## 10. Session DB size — `REPORT`

- **Where:** `$HOME/.opencrabs/profiles/ops/opencrabs.db`
- **Invariant:** Warn if SQLite database file exceeds 1 GB.
- **Remediation:** Report to operator/Toolsmith.

## 11. `tools.log` JSONL integrity — `QUIRK` (report only)

- **Where:** `$OC_DEV_STATE/tools.log` (`OC_HEALTH_LOG` overrides).
- **Invariant:** Total line count must match JSON-parsable lines (`jq -Rr 'fromjson? | .ts'`).
- **Remediation:** Report only — never rewrite or delete audit evidence.
  Known historical non-JSON evidentiary lines (e.g. line 443 actor-correction) remain immutable.

## 12. Detached watcher compliance — `WARN` (report only)

- **Where:** `$HOME/.opencrabs/profiles/ops/tmp/detached/*.json` (`OC_HEALTH_DETACHED_DIR` overrides).
- **Invariant:** No detached task inside the **rolling window** may run `gh run watch`
  with no `--interval` (the forbidden 3s default) or at an interval other than 30/60;
  no `nohup` launches; no hand-rolled `while … sleep` pollers.
- **Window:** `OC_HEALTH_WATCHER_WINDOW_H` (default **24**; `0` = all history). Tasks
  spawned before `now − N hours` are not re-audited, so a long-terminal task stops
  re-alarming once it ages out.
- **Count semantics:** the finding carries the **real** number of violations plus a
  per-type breakdown (`[UNTHROTTLED_WATCHx3 NOHUP_SPAWNx1]`) and the count of
  violations whose task state is still `Running`. A payload that cannot be parsed is
  a **measurement failure** (`QUIRK unthrottled-watch-unparsed`, rc 3), never a
  fabricated count.
- **Remediation:** Report only — the audit names the offending lane; a sweep must not
  rewrite another lane's detached-task record.

## 13. Ledger JSON integrity — `URGENT` (report only)

- **Where:** `$OC_DEV_STATE/workers-ledger.json`.
- **Invariant:** File parses as JSON.
- **Remediation:** Report only; corrupting evidence is never the fix.

## 14. Ledger roster consistency — `QUIRK` (report only)

- **Where:** `$OC_DEV_STATE/workers-ledger.json`.
- **Invariant:** Every enrolled worker carries the fields the roster verbs require.
- **Remediation:** Report only — HQ owns roster repair.

## 15. Tool failure-rate — `REPORT`

- **Where:** `$OC_DEV_STATE/tools.log` (`OC_HEALTH_LOG` overrides).
- **Invariant:** For any tool with ≥10 invocations, a failure rate above 15% is reported.
- **Remediation:** Report to operator/Toolsmith — a high-rate tool is a tool defect signal.

## 16. Daemon error volume — `WARN` (report only)

- **Where:** `$HOME/.opencrabs/profiles/ops/logs/opencrabs.<today>`.
- **Invariant:** Warn above 50 ` ERROR ` lines in the current UTC day.
- **Remediation:** Report only. A nonzero baseline is expected: ordinary non-zero tool
  exits (`[TOOL_EXEC] … failed: code X`) are logged as errors, so the check flags
  volume, not correctness.

## 17. Issue claim structure — `REPORT`

- **Where:** `$OC_DEV_STATE/workers-ledger.json` claim events.
- **Invariant:** No open claim without an owning session uuid.
- **Remediation:** Report to Triage/HQ, who own issue routing.

---

## 18. Registered-worktree tracked-file deletion — `REPORT` (warn)

- **Where:** every registered worktree of `$OC_HEALTH_FORK` and `$SKILL_CHECK`, via `git worktree list --porcelain`.
- **Invariant:** porcelain ` D` (tracked file deleted in the worktree, NOT staged) is never a legitimate mid-work state — a deliberate removal is staged by `git rm` and then reads `D ` in the INDEX column, so a lane mid-work cannot trip this. The staged form is a DIFFERENT condition and is deliberately NOT flagged.
- **Remediation:** Report only (`git checkout -- <path>` in the affected tree, or stage the removal). Removing the tree itself stays `tools/git/oc-wt remove`.
- **Quirk:** n/a — the finding IS the signal.

---

## Never touch (evidence / live state)

- `workers-ledger.json` itself, `tools.log`, `journal/`, `incident-evidence-*`,
  `reviews/`, `designs/`, `smoke-verdicts.log`, `orders.json`, `baseline.json`.
- Any file held open by a live PID.
- Any worktree with a dirty tree (uncommitted work).
- Historical evidentiary entries in logs/ledgers.

## Escalation

- **Quirks:** Single-line summary naming the object/lane and failed check.
- **Clean Bill:** Explicitly report objects checked and 0 findings (silence is not a receipt).
- **Recurring Quirks:** Escalate to HQ when the same check fires repeatedly across cycles.
