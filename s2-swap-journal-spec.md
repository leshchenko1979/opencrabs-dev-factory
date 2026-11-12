# S2 swap-leg journal spec — for oc-deploy wiring (live since v0.4.62; title "(proposal)" retired lens A13 v0.4.89)

Author: compiler lane e756b84b · 2026-08-28
Answers: owner tool-logging law 2026-08-28 (fleet-directives.md §Tool logging rule) + HQ ledger-1264 gap list
(no Aug-28 backup entry; deployed.sha never written during the 03:11Z swap).

> **AMENDED 2026-08-28 18:50Z (owner order — consent eliminated):** the
> `consent` journal line type below is superseded by the `auto-swap` line
> (`reason=green-run`, `consent:"eliminated-owner-2026-08-28"`); `deployed.meta.json`
> carries `auth:"auto-swap"` instead of `consent_msgid`. Everything else in this
> spec (journal vocabulary, markers, reconstructability law) stands unchanged.

## Law being satisfied

Every state-changing step writes a timestamped, append-only journal line (input,
action, outcome, exit code) to durable storage BEFORE the next step begins. If a
crash or restart can leave a run unreconstructable from journal + markers alone,
the tool is NOT DONE. Chat-scroll archaeology is failure.

## Journal location

`STATE_DIR/oc-deploy/journal/swap-<short-sha>-<epoch>.jsonl` — one file per swap attempt,
append-only, every line fsync'd before the next step starts. (Live oc-deploy
writes the 8-char short sha + an epoch suffix — the epoch disambiguates repeat
swaps of the same sha.) STATE_DIR = the state
dir oc-deploy already owns for `deployed.sha`.

## Line shape (one JSON object per line)

```json
{"ts":"<RFC3339Z>","step":"<name>","seq":<n>,"exit":<int|null>, ...step fields...}
```

`seq` monotonic per file. A missing line after a crash pinpoints the crash step:
last present line = last completed step.

## Required swap-leg line vocabulary (extends existing `dispatch`)

| # | step | fields | when |
|---|------|--------|------|
| 1 | `dispatch` | (existing) order sha, run_id | dispatch lands |
| 2 | `consent` | sha, kind=deploy, msgid, topic, quote | **RETIRED 2026-08-28 18:50Z** (superseded by `auto-swap` — see amendment above; kept for historical journal parsing) |
| 3 | `backup` | backup_path, backup_sha256, bytes | immediately after backup created. Skip → exit≠0 + skipped_reason; prod swap MUST NOT proceed |
| 4 | `verify` | run_id, source_ref, artifact_sha256, features, verify_exit, provenance | after oc-artifact-verify; verify_exit≠0 HALTS |
| 5 | `install` | old_sha256, new_sha256, bytes, method=install+mv | after atomic mv |
| 6 | `seal` | baseline_path, cycle, seal_exit | after oc-seal-state; seal_exit≠0 HALTS before restart |
| 7 | `restart` | unit, systemd_run_exit | chained unit accepted |
| 8 | `post-verify` | is_active, disk_sha256, expected_sha256, match | post-bounce leg, from the chained unit's output |
| 9 | `marker-write` | deployed_sha_path, deployed_sha, wrote | after marker write (below) |
| 10 | `receipt` | topics[], message_ids/session_notify ids | after receipts posted |
| 11 | `rollback` | restored_backup, restored_sha256, reason | conditional; restart+post-verify lines repeat after it |

## Marker writes (the 03:11Z gap — HQ had to hand-restore)

The swap tooling itself writes, between `seal` and `restart` (so markers reflect
intent even if the restart crashes):

- `STATE_DIR/deployed.sha` — the full 40-char source sha + newline
- `STATE_DIR/deployed.meta.json` — `{sha, run_id, artifact_sha256, features, swapped_at, auth:"auto-swap", prev_sha}` (live marker shape — no `consent_msgid`, consent eliminated 2026-08-28)

`post-verify` re-reads both; any mismatch or absence → its journal line carries
exit=1 and the swap is reported UNSEALED even if the binary answers health.

## Mandatory ledger stamp

Every swap attempt (success OR rollback) ends with a workers-ledger stamp:
`kind="swap-result"`, lane, sha-bound, body quoting journal lines 5+8+9
(install + post-verify + marker-write). Ledger stamp failure ⇒ swap reported
UNSEALED regardless of binary health; the next cron/human check treats UNSEALED
as an incident. No receipt post before the stamp lands.

## Acceptance criteria

**(1) PRIMARY — behaviour after the swap:** the running unit answers as the target
build (`oc-deploy status` matches disk) AND a live probe of the swapped feature's
own path passes. A swap is not accepted on journal completeness alone.

**(2) SECONDARY — reconstruction:** `kill -9` a staging swap mid-flight; from
journal + deployed.* markers ALONE an operator must answer which binary is on
disk, which step crashed, and whether auth (auto-swap) covered the attempt. Any
answer requiring chat history = the reconstruction leg is not met.

## Fan-out legs (re-homed from SKILL.md §Session-notify loop, v0.4.80 — lens B F4)

- After a healthy swap the fan-out extracts contributors over
  `<prev-swapped-sha>..<verified-run-headSha>` (right edge = the run's VERIFIED
  headSha, never "current main" — a merge landing mid-build leaves main ahead of
  the binary), notifies each contributing editor's session
  about the new binary, then records `{sha, run_id, contributors}` to the
  baseline state file (`oc-seal-state`; canonical:
  `/root/.opencrabs/profiles/ops/opencrabs-dev/baseline.json`) — its `sha` is
  the left edge of the next attribution range. LIVE since v0.4.37: `oc-deploy
  fanout --run <id>` ([#24](https://github.com/leshchenko1979/opencrabs/issues/24),
  on top of the [#23](https://github.com/leshchenko1979/opencrabs/issues/23)
  session-notify verb `49125f8c`). GREEN leg: git-range → trailers →
  `opencrabs session notify --profile ops`, dead uuid = journal `skip` + note;
  auto-fired at the `swap_execute` tail, idempotent via `fanout.state`;
  `--dry-run` journals but never notifies or marks done. RED leg (`poll` scans
  the latest FAILED run): gh annotations → `git blame` → culprit `Session-Id`
  trailer notified (`role=blamed`), suspect cc on same-file later touchers,
  zero-sites fallback HUMAN-FLAGs all range sessions. Both legs suppressed by
  `OC_DEPLOY_NOFANOUT=1` (drills), subshell-isolated. Journal:
  `/root/.opencrabs/profiles/ops/opencrabs-dev/oc-deploy/journal/fanout-<run>-*.jsonl` (state dir since v0.4.60), steps `fanout-start /
  contributors / attributed / notified / skip / unowned / fanout-end`.

**The notified sha may not be the RUNNING sha — resolve by IDENTITY, then smoke the running binary (v0.4.218, filed by lane c10cd97b; its `target=` clause amended per the HQ ruling below).** A fan-out names the sha whose range attributed your commits, and the box swaps on its own cadence — so by the time a lane reaches its smoke phase the notified sha is frequently superseded. The filing lane's own measurement: the notice for run `35441550360` named `b2823127` (swapped 12:14:45Z, so the notice itself lagged the swap by 22m33s), and six distinct shas were swapped across the 12:14:45Z–15:14:40Z window (span 2h59m55s, mean inter-swap gap 36.0 min) with 17 across the day. A mean gap shorter than a typical lane's design→ship→smoke cycle makes "the notified sha is no longer live" the NORMAL case, not an edge. Resolve the collision from LIVE STATE, never from the notice:

1. Read the running identity (`oc-smoke-evidence`, bare) and the notified sha.
2. **Still live** — smoke it; row `PASS`, `sha=` = that sha.
3. **Not live** — verify LINEAGE first: `git merge-base --is-ancestor <notified-sha> <live-sha>`, rc 0. A live sha that DESCENDS from the notified sha contains the notified work, so the smoke is owed against the LIVE binary and the row cites `sha=` = the LIVE sha. If rc ≠ 0 the tree was rewritten — that is the `CORRECTION` case (post-lineage-rewrite re-verification), not this one.
4. **Never cite a sha you did not drive.** A row whose `sha=` names the notified sha while the probe ran against a newer binary is a FALSE receipt.

**`target=` in such a row is NOT the discharged sha — it is the unit, and the discharge goes in `evidence=`.** `target=` carries the DEPLOYMENT UNIT (`live-ops` by default) — definition lives in `upstream-merge-runbook.md §Ledger hygiene laws`, the `target=` bullet; do not restate it here. A lane that writes the notified sha into `target=` while `sha=` names the live binary splits one key into two meanings, and a consumer reading by key cannot tell which convention a row follows. Write `sha=` = the LIVE binary driven, `target=` = the unit, and carry the link the fan-out exists to create in `evidence=discharged-notified-sha=<sha>`.

**Cost of the gap (why this is codified).** Lane `c10cd97b` resolved it by hand — lineage-checked each of its commits against the live sha, then stamped a `CORRECTION` row — because both neighbouring outcomes survived review unchallenged: citing the NOTIFIED sha in `sha=` while driving a newer binary looks like a receipt but names a build the probe never touched, and citing the LIVE sha with no discharge link loses the attribution the fan-out exists to create. Neither was prohibited, because the case was unstated.

## Post-swap notify (LIVE — mechanical fan-out since 2026-08-29)

Mechanics canonical: `oc-deploy fanout` (GREEN leg at the swap_execute tail, RED leg via poll failed-run scan; idempotent `fanout.state`; drills off via `OC_DEPLOY_NOFANOUT=1`) + s2-swap-journal-spec §Fan-out legs. No manual notify steps anywhere. Ledger path is canonical `opencrabs-dev/workers-ledger.json` — the skill-dir duplicate was deleted 2026-08-29 (v0.4.38); fix shipped FIRST, deletion second.

**Fanout commit sweep excludes upstream merge ancestry (Duty-4 P-01, v0.4.133):** `oc-attrib --contributors --first-parent` strictly sweeps `--first-parent` for deployed commit attribution, preventing traversal into foreign upstream merge ancestry. Upstream sync merge commits (e.g. `8870bd40`) will NOT falsely wake completed historical editor lanes whose Session-Ids appeared in merged PRs.

**Second, independent exclusion on the SAME sweep — the novelty filter (issue #407, v0.4.212):** `--deployed` now IMPLIES `--novel`, so the sweep additionally drops (a) commits whose change is ALREADY in the baseline (patch-id equivalence via `git cherry <baseline> <tip>` — i.e. every re-sha'd twin a rebase or sync produces) and (b) EMPTY commits (non-merge, no changed paths — no patch-id, so `git cherry` can never match them). Merges pass through UNFILTERED (`git cherry` omits them, so a membership test would silently drop every one). This is the exclusion that covers the REBASE case the `--first-parent` rule above does not mention; the two are independent and both apply. A deployed range that yields ZERO contributing rows after the filter is **rc 0 GREEN** with `no novel commits in range` — never an attribution failure and never rc 3. `--no-novel` is the escape hatch that restores the raw range.
