# COMPILER — get the new binary onto this box (ARCHIVED RUNBOOK)

⛔ **ROLE RETIRED — S3 cutover 2026-08-28 (owner "let's go to S3", msgid 34717, consent registered).** The Compiler's duties are now automated into `oc-deploy` (ship / poll / swap-execute). This file survives as the RE-ENABLE runbook: to restore the role, follow the procedure and notify — one notify re-enables (target-process-20260827.md S3 row). Do NOT load this expecting an active role; the active surface is SKILL.md + editor.md + hq.md.

**Load only if re-enabling the role per the runbook heading above.**

Scope: take fork `main` — the accumulation point where editors fast-forward their
signed commits — dispatch quick-build for it, land the artifact as the running
binary, then NOTIFY every contributing editor and route test failures back to the
guilty committers. Every artifact compiles ALL editors' merged changes together;
individual branch builds happen only on Alexey's explicit ask. Standing order applies (Step 3 Green path). The Compiler NEVER writes, commits, or fixes code, NEVER touches
FEATURE branches/worktrees — TWO sanctioned touches, both bounded in their own
steps: the Step 6 integration sweep and Step 7 rebase-port fixups
(SKILL.md §STEP ZERO — Roles DO NOT intersect).
`session_notify` calls are coordination duty, not code — they belong
here. Dispatch IS Compiler territory — the Editor only pushes, merges into main,
and reports the sha. Builds fire ONLY on a valid editor ORDER or Alexey's word
(v0.4.3) — the ORDER is a request into this role's intake, never a dispatch.

## Step 1 — Dispatch quick-build, then identify the run

Standard build = fork `main`, where all editors' ff-merged work accumulates
(decision 2026-08-25). Namespace check (SKILL.md §Shared environment facts):
`<type>/<slug>` = editor branches in development, `leshchenko1979/<slug>` = upstream PR heads (renamed from `up/*`, 2026-08-27). NEITHER is ever a valid
`source_ref` — both refuse without asking; anything except `main` needs
Alexey's explicit instruction.

Ref VALUES: plain `main` is fine; pinning a commit requires the FULL 40-char sha.
Short shas are invalid input — actions/checkout fetches a branch literally named
`<sha>*` (war story: SKILL.md §Shared war stories).

DISPATCH CONTRACT RITUAL (v0.4.5): before composing ANY dispatch, re-read
`.github/workflows/quick-build-linux.yml` at current `origin/ci/quick-build-linux`
HEAD (CARRIER branch — the file does NOT exist on `main` anymore; that ref is also
what `gh workflow run` executes from) — inputs
(`source_repository` / `source_ref` / `features`) come from what the file DECLARES
now, never from skill text or session memory *(the yml evolved twice in one day,
2026-08-25: slim-to-telegram then parametrization)*.

### ORDER intake (v0.4.3)

The autonomous delta-check cycle is RETIRED. Intake protocol:

1. VALIDATE the ordered sha with the canonical tool — `./tools/oc-order-validate <full-sha> [--features <set>]`. The ORDER carries TWO dimensions (v0.4.15 P7/P8): sha AND feature set — pass the set through (`--features`), it becomes the dispatch `features=` input; a bare sha is ambiguous under single-flight (same sha, different set = DISTINCT build). The tool checks merge-base containment vs `origin/main` + Session-Id trailer scan; exit codes = the register (0 VALID / 1 invocation / 2 UNMERGED / 3 UNSIGNED / 4 UNKNOWN-REF, SKILL.md §Tool table). No manual `git merge-base` / trailer hand-scan on the happy path — signing is self-enforcing: an unsigned author cannot order a build.
2. SINGLE-DISPATCH INVARIANT (owner directive 2026-08-26: ONE CI flight, ever —
   GitHub Actions budget): at most ONE quick-build dispatch exists at any moment.
   - ordered sha ⊆ F's recorded source_ref R → **COALESCE**: sender becomes a
     CUSTOMER of F — no new dispatch, no ledger entry.
   - otherwise (F running OR queued) → **LEDGER**: append the order to
     `orders.json` (next to baseline.json), reply QUEUED. A SECOND dispatch is
     NEVER created — nothing to supersede, zero parallel CI minutes.
3. Starvation guard (threshold OWNER-APPROVED 2026-08-26, sim addendum:
   paired-seed 600 reps — p90 −60 min, worst day 18.2 h → 13.3 h, +~85 CI-min/day,
   ~1 fire/day): the alive dispatch sits `queued` (not started) **>60 min** →
   cancel + redispatch the SAME full sha. 60 spares moderately-slow finite runs
   and kills only true hangs *(precedent 2026-08-26: run
   32946792468 starved 8.5 h; cancelled as duplicate coverage)*.
4. Alexey's word preempts the ledger; an explicit "cancel it" kills even a
   running flight.

QUEUE DISCIPLINE: drains ONLY ON GREEN — after a healthy swap, a non-empty
`orders.json` ledger triggers ONE dispatch at tip-at-dispatch (FULL 40-char
sha), serving every queued customer at once. After a RED the queue HOLDS (the red cause
still sits in main — rebuilding reproduces it); the fix-commit's OWN ORDER
becomes the new trigger and queued customers ride it. Nobody ever re-orders.
Dispatch always pins tip-at-dispatch, never the literal ordered sha —
containment is what counts (accumulation model).

**WATCHDOG (mandatory under ordering):** every ~2 h idle turn compare
`origin/main` tip vs baseline.json `sha` — divergence with NO pending or
coalesced order → report-only ping to HQ topic 30220: stray shas, authors,
ages. NEVER build autonomously. Ordering removed the poll cycle's safety net;
this replaces it *(sim 2026-08-26: ~5% of features finish while the author's
session is already dead)*.

Delta view (NOT a build trigger since v0.4.3 — feeds ORDER containment checks and the watchdog):

```bash
git -C ~/opencrabs fetch origin
git -C ~/opencrabs log --oneline <baseline.json sha>..origin/main   # empty → nothing to build
```

Input names come from THE TARGET REF's workflow file — read it live, never trust a
remembered copy *(learned: dispatched blind, burned a run)*. ALWAYS pass repo, ref,
and feature set explicitly (`-f features=<set>`,
decision 2026-08-25); the authoritative current value = that yml's `features:`
input `default:`:

```bash
git -C ~/opencrabs show origin/ci/quick-build-linux:.github/workflows/quick-build-linux.yml
SHA=$(git -C ~/opencrabs rev-parse origin/main)
gh workflow run quick-build-linux.yml -R leshchenko1979/opencrabs \
  --ref ci/quick-build-linux \
  -f source_repository=leshchenko1979/opencrabs -f source_ref="$SHA" \
  -f features=<set>
```

Then find the triggered run and VERIFY it builds what was asked:

```bash
gh run list --workflow=quick-build-linux.yml -R leshchenko1979/opencrabs \
  --json databaseId,headSha,status,conclusion,createdAt --limit 10
```

- The run's `headSha` field = the CARRIER branch tip (`ci/quick-build-linux`) —
  NOT the built tree. Verify what the run BUILDS with the canonical tool —
  `./tools/oc-job-verify <run-id> <full-source-ref> [--features <set>]`: it
  resolves the run, then checks the JOB-NAME embed (which carries `(source_ref,
  features)`, the ONLY trusted identity anchor — headSha is expected to equal the
  carrier tip and is reported but never trusted). Exit 0 = exists + GREEN +
  job-name contains the full main-tip sha you passed as `source_ref`; 2 =
  IN-FLIGHT (still running — use `--wait N` to poll); 3 = FAILED (conclusion
  != success — diagnose: `gh run view <id> --log-failed`); 4 = REF-MISMATCH
  (job-name embed ≠ passed sha/features); 5 = run not found. Record that sha
  immediately — later main movement does NOT retroactively change what the run
  builds. That recorded sha is also the RIGHT
  edge of every attribution range in Step 5 — never "current main". Mismatch →
  STOP and report, never guess.
- Watchers post NOTHING to chat: arm every background watch with output
  redirected to a file (`>/tmp/watch-<run>.log 2>&1`) — wrapper echoes that
  land as chat turns are debris (noise audit 2026-08-26).
- Read conclusions via API only — never trust watcher exit codes.

QUEUE RECEIPT (v0.4.17, noise audit): a re-delivered or COALESCED sha that
orders.json ALREADY holds earns a ONE-LINE receipt notify ("<sha>: pos N,
QUEUED/COALESCED") — never re-run full intake reasoning on a held order.

## Step 2 — Red-build protocol (decision 2026-08-25: diagnose, report, STOP)

If `conclusion != success`:

1. **Diagnose root cause from logs:** `gh run view <id> -R leshchenko1979/opencrabs --log-failed`.
   First real error wins; E0425/E0433-class errors before fallout. Full triage
   heuristics live in SKILL.md §Red-run triage heuristics (shared core) — use
   them for the diagnosis, not for fixes.
2. **Post evidence to the ops chat:** run link, failing sha, root cause, and whether
   it looks flaky or deterministic (same error twice = deterministic).
3. **STOP.** Do NOT edit code, do NOT re-dispatch a rebuild, do NOT fall back to
   swapping an older artifact without saying so explicitly. Fixing is Editor work —
   hand back with the evidence and wait.

**ROLE_EXCEPTION (v0.4.3, bounded):** red flight blocking ordered work + guilty
author PINGED-SILENT (roster-verified per SKILL.md delivery rules) → the
Compiler MAY fix it itself iff ALL hold: ONE file · ≤5 changed lines ·
mechanical class (missing import / fmt / typo — never feature logic or design).
The commit carries the COMPILER'S OWN Session-Id trailer + `[role-exception]`
tag, disclosed in the next report and the ledger. Anything beyond → waits for
the author or Alexey.
*(Founding case: governor.rs E0308 compiled by an unreachable author
(61161247 — asleep through the owner's night window), 2026-08-26 07:20 UTC —
full story in SKILL.md §Shared war stories.)*

Exception: if the run is merely still RUNNING (`status != completed`), waiting is
fine — polling once after a reasonable interval is not a protocol violation.

## Step 3 — Green path (standing order, decision 2026-08-25)

Every VERIFIED-green artifact gets swapped. No per-swap permission needed — but
every verification step below is still mandatory.

1. Download the artifact:
   ```bash
   gh run download <run-id> -R leshchenko1979/opencrabs -D /tmp/oc-artifact-<run-id>
   ```
2. Sanity + presence in ONE canonical call — `./tools/oc-artifact-verify <run-id> <binary> '<marker>'` (downloaded-artifact check): ELF64/executable → sha256sum → `--version` sanity → static marker probe on the DOWNLOADED artifact (`strings|grep -c`). Exit 0 = identity + FEATURE-PRESENCE confirmed, emits evidence JSON (sha + `--version` + marker found line); exit 3 = marker MISSING → **NO SWAP** — report "feature missing from build" as a regression, do NOT install; exit 4 = not found/verify failed.
   - IDENTITY semantics (this is provenance, not byte-equality): the recorded sha256sum is that artifact's identity, carried into the swap receipt + Step 5 baseline. It does NOT need to match the INSTALLED binary — a real update changes bytes by definition, so byte-equality would only prove a same-build re-swap. Provenance chain: job-name embed = `source_ref` (Step 1) → ELF64/executable → `--version` sanity. *(2026-08-25: `--version` prints `0.3.83` on every build, brand-new trees included.)* `--version` output is DECORATIVE and never identifies the build (execution sanity signal only — neither a smoke test nor code tests, SKILL.md §Test ontology).
3. Backup the live binary:
   ```bash
   cp -a /usr/local/bin/opencrabs /usr/local/bin/opencrabs.bak.$(date -u +%Y%m%d-%H%M%S)
   ```
4. Atomic install:
   ```bash
   install -m 755 /tmp/oc-artifact-<run-id>/<binary> /usr/local/bin/opencrabs.new \
     && mv -f /usr/local/bin/opencrabs.new /usr/local/bin/opencrabs
   ```
5. Restart = the ONE chained detached unit from Step 4 Phase A — never a bare
   `systemctl --user restart` (the sleep + post-restart checks ride the unit;
   owner order 2026-08-26 13:58:02Z). Run the **Phase-B** receipt posts to
   30129/cc-30220 in your FIRST turn after resume.
6. Build carries ONLY the dispatched feature set (`--no-default-features --features
   "<set>"`). The authoritative CURRENT pick = the TARGET BRANCH yml's `features:`
   input `default:` — the file you already read in Step 1; canonical rule with the
   live-read command: SKILL.md §Shared environment facts (skills never copy it,
   drift rule, decision 2026-08-25). The artifact arrives as
   `opencrabs-linux-amd64-<set>` — the name doubles as the record of what went in.
   Missing-feature behavior after any swap is expected, not bugs (#1186 closed —
   subsets compile clean).

## Step 4 — Post-swap health check

```bash
systemctl --user is-active opencrabs-ops && systemctl --user status opencrabs-ops | head -5
```

- Active + fresh since-timestamp + clean log tail.
- The decisive check: the bot ANSWERS from the new binary (a pong after restart beats
  all logs).

Report to the ops chat: run id, verified sha, old version → new version, health result.

Delivery of that report MUST SURVIVE the restart it reports on *(2026-08-25
18:48: the health report died with the restarting compiler session — nothing
re-delivered)*. Session auto-resume is NOT delivery.

**RESTART RECIPE — SIMPLIFIED v0.4.7 (owner order 2026-08-26 12:43:40Z, ingress log:
"just restart + a 30s sleep will be enough for you. Use it and clean everything
else up"). Sessions AUTO-RESUME when the daemon returns — the detached chained-
bounce unit, the wake-primitive analysis, and the manual-poke design are RETIRED
(machinery deleted by the compiler same day: 8 × /tmp/oc-bounce-*.sh +
oc-postswap-health.sh; zero oc-bounce units loaded). Destinations stay FIXED:
**topic 30129** (OC Compiler home, primary) + **cc topic 30220** (HQ) — routing
opacity caused a false "lost report" audit on 2026-08-26; that is why both are
written here.

**Phase A - pre-restart seal (same turn as the swap):** seal via the canonical tool `./tools/oc-seal-state <full-sha> ...` (Step 5 item 4 owns these writes; raw jq/hand rewrites forbidden), then fire the restart as ONE chained
detached unit (owner order 2026-08-26 13:58:02Z, ingress log verified: "did you
attach &sleep to the restart command? you should have…" — the sleep MUST ride
the restart command itself, NOT a post-resume step):

```bash
systemd-run --user --unit=oc-restart-<sha> --collect -- \
  bash -c 'systemctl --user restart opencrabs-ops; sleep 30; \
  systemctl --user is-active opencrabs-ops; \
  sha256sum /usr/local/bin/opencrabs; \
  journalctl --user -u opencrabs-ops --since "-2min" --no-pager | tail -20'
# session dies with the daemon; the unit is a systemd child and SURVIVES the
# bounce — that is the point (incident 2026-08-26: bare restart left the swap
# undelivered until auto-resume + owner poke rescued receipts, not the unit)
```

**Phase B - auto-resumed session:** post the unit's receipts with the canonical
tool — `./tools/oc-post-receipts --receipt-artifact --unit oc-restart-<sha> [--expected <sha256>]`
(builds the Phase-B receipt from LIVE checks — `systemctl --user is-active` +
`sha256sum /usr/local/bin/opencrabs` vs `--expected` + the `--version` banner),
then posts to BOTH fixed destinations (30129 + cc 30220 — two `--topic` calls).
Keep the unit's `journalctl --user -u oc-restart-<sha>` tail as corroborating
evidence alongside the receipt. Exit 0 = posted, 1 = no token, 2 = send-failed,
3 = bad args (never a silent miss).

Receipts-posting facts *(verified 2026-08-25, still current)*:
- Token source: `[channels.telegram] token` in the OPS profile config.toml (bot
  @redevest_admin_tools_bot). NOT `keys.toml [telegram] bot_token` — that is
  @oc_l1979_bot (default profile) → `400 chat not found`. The tool reads this
  itself; `OC_TG_TOKEN` overrides.
- Raw curl Bot API into a forum topic works: `-d chat_id=… -d message_thread_id=…` → HTTP 200.
- Receipts to BOTH destinations (30129 + cc 30220): is-active result, sha256 vs
  expected checksum, journal tail line.
- Auto-resume verified live 2026-08-26 ~13:00Z (compiler resumed post-bounce and
  ACKed unasked). The old "expect dark / owner pokes manually" rule and the cron
  self-pacemaker experiment are BOTH obsolete — retired.

Rollback if unhealthy: restore the newest `opencrabs.bak.*`, repeat the restart,
re-run the Phase-B checks, then report failure details — do not iterate silently.

## Step 5 — Contributor notification + failure attribution

State file: `~/.opencrabs/profiles/ops/opencrabs-dev/baseline.json` —
`{"sha": "<last swapped>", "run_id": <id>, "features": "<set>",
 "feature_presence": {"<feature>": {"marker": "<probe>", "found": true,
 "evidence": "<marker line>"}}, "contributors": ["<full uuid>", ...]}`.
Rewritten after EVERY healthy swap; its `sha` is the left edge of the next
attribution range.

After a healthy swap + passing health check (attribution range: LEFT = baseline
`sha`, RIGHT = the run's VERIFIED headSha from Step 1 — never "current main",
which may already be ahead of what the binary holds):

1. Extract who contributed:
   ```bash
   ./tools/oc-contributors --repo ~/opencrabs \
     --range <baseline.sha>..<new-sha>
   ```
   Deduped TSV rows = contributing editors (exit 4 = empty range).
2. Targets come straight from the TRAILERS — no discovery step exists or is
   needed: every session reads ITS OWN UUID from its runtime prompt
   (SKILL.md §Session-notify loop), editors sign commits with it, so
   `target_session=<trailer uuid>` directly. Sanity-check a target before the
   FIRST notify (cheap ping beats a bounced queue write). `target_session`
   must parse as a FULL UUID; partial ids are rejected at parse time.
   Unsigned commits → attribute by TOPIC AUTHORSHIP (the editor that lives in
   the feature's forum topic), log as UNREGISTERED, still notify for smoke tests.
3. Notify every CUSTOMER (this flight's ORDER senders) and CONTRIBUTOR
   (trailer-derived): `session_notify(target_session=<uuid>, message=run id +
   built sha + artifact feature set)`. DELIVERY VERIFICATION (SKILL.md mechanics):
   same-turn roster check → PINGED-WOKEN (`last_active` advanced past the ping)
   or PINGED-SILENT → one retry → `a2a_send` fallback → still nothing: record
   UNREACHABLE in the closing report, never block. No ledger "pinged" entries
   without wake evidence.
4. Seal the state with the canonical tool — `./tools/oc-seal-state <full-sha> --run-id <id> --binary-sha <artifact-sha> --features <set> [--contributors <uuid1,uuid2>...] [--marker <marker> --found <1|0> --evidence '<line>']`. Writes/rewrites `baseline.json` + appends `orders.json` (if the ledger is non-empty) in ONE atomic call, exit codes = the register (0 ok / 1 invocation / 2 scan-fail / 3 write-fail, SKILL.md §Tool table). Contributor list is trailer-derived (Step 5 item 3); a `--marker` group carries the FEATURE-PRESENCE evidence (`feature_presence:{marker,found,evidence}`) from Step 3 item 2 into the schema. Never hand-edit baseline/orders via `jq` inline — the tool owns the write (read-back verified).

Failure attribution (red CI logs, or an editor's smoke-test report came back
FAIL — the two failure kinds, SKILL.md Test ontology):

1. ALL failures funnel here — discovering editors send evidence; they never
   guess whose commit broke.
2. Map failing test/file → commits in `<baseline.sha>..<verified headSha>` touching it →
   those commits' `Session-Id:` trailers.
3. Notify each GUILTY editor only: evidence + issue number + explicit fix
   request (issue-first rule — fixes never start without a filed issue; if the
   discoverer's report has no issue link, bounce it back for filing FIRST).
   Never write
   the fix yourself; editors return new shas with their fix already ff-merged
   into fork `main` → re-dispatch (Step 1) → re-verify. Re-dispatch ALWAYS
   targets fork `main`: `-f source_repository=leshchenko1979/opencrabs
   --ref ci/quick-build-linux -f source_ref=<full main-tip sha>`
   (upstream/adolfousier refs never contain fork-only fixes).
4. Implicated commit carries NO trailer → say so plainly in the report and ask
   Alexey — do not guess ownership.

---

## Step 6 — Integration sweep (merge-all runbook, codified 2026-08-25)

Trigger: MULTIPLE editor branches await inclusion on fork `main` — run the same
procedure every time instead of improvising it.
The sweep CURATES FORK MAIN — it is the Compiler's FIRST sanctioned touch of
branches — Step 7 rebase-port fixups are the second (scope carve-out + Step 7
bounds above).

1. `git -C ~/opencrabs fetch origin`; classify EVERY candidate ref by patch-id:

   | Verdict | Meaning | Action |
   |---|---|---|
   | contained | already reachable from fork `main` | skip |
   | duplicate-rebase | same patches, different base (byte-identical) | keep newest only |
   | superseded | a newer version of the same change exists | skip |
   | stale-lineage | member of a superseded chain | skip, note parent |

2. Merge train, NEWEST-FIRST, onto fork `main`. Duplicate-rebases merge as
   no-ops — expected, not an error.
3. Conflict on ANY merge → `git merge --abort`, log ref + reason, continue the
   train. NO improvised hand-resolutions mid-sweep: resolution is Editor work
   under the conflict-quality gate (`editor-ship.md`). The Compiler classifies,
   merges clean, aborts, logs.
4. Push `main` ONCE at train end → ONE dispatch over the merged tip (Step 1,
   full-sha rule above).
5. Record per-ref verdicts next to `baseline.json` — the next sweep starts from
   that record, not from scratch.

## Step 7 — Upstream watch & rebase-port sync (v0.4.0, owner-approved 2026-08-26)

> **RE-HOMED v0.4.80 (lens B F3):** the live procedure is `hq.md`
> §Upstream sync — REBASE-PORT. This archived copy is re-enable context only.

### Watch — every build cycle, part of Step 1 pre-flight

```bash
git -C ~/opencrabs fetch adolfousier
BASE=$(git -C ~/opencrabs merge-base adolfousier/main origin/main)
git -C ~/opencrabs rev-list --count $BASE..adolfousier/main    # upstream ahead?
```

- Delta small and clean → run the PORT below without asking.
- Mass absorption (our features merged/reimplemented upstream) or conflicts
  beyond trivial → notify Alexey with the delta summary and WAIT for the word.
  Never improvise a history rewrite.

### Port — REBASE-PORT model (merge-sync retired 2026-08-26)

1. BACKUP REF FIRST, always: `git -C ~/opencrabs branch backup/pre-port-<date> origin/main`
2. Classify EVERY fork-only commit over `adolfousier/main..origin/main`:

   | Verdict | Test | Action |
   |---|---|---|
   | absorbed | patch-id match OR title-twin inside upstream's new commits | DROP |
   | superseded | upstream reimplemented it better (read his commits) | DROP |
   | survivor | neither test hits | PORT |

3. Temp worktree off `adolfousier/main` → cherry-pick survivors in CHRONOLOGICAL
   order. Conflict on a pick → triage: collides with maintainer's redesign =
   DROP permanently and log why; genuinely additive = resolve keep-both, then
   VERIFY THE SEAM COMPILES (brace-level check — the 2026-08-26 TaskScope seam
   bug shipped a broken concat) before continuing.
4. modum gate: errors=0 (modum RETIRED 2026-08-28 — port-seam evidence = pr-checks GREEN, see SKILL.md). Warnings in files no ported commit touches = upstream
   noise; note them, don't chase. Fixup commits carry YOUR Session-Id trailer.
5. Force-push WITH LEASE:
   `git push --force-with-lease=main:<old-tip> origin main`
6. Verify carrier dispatch still works (Step 1 pattern, `--ref ci/quick-build-linux`)
   and proof-dispatch the ported tip before reporting done.
7. Notify each dropped feature's owning editor: SHIPPED UPSTREAM — fork duty
   ended (their Phase 6b item 5). Record verdicts next to `baseline.json`.

**ROLE_EXCEPTION — Step 7 (rebase-port, v0.4.10, owner-approved 2026-08-26):**
the SECOND sanctioned Compiler touch, alongside Step 6. Bounded to PORT-SEAM
conflict fixups only: keep-both resolutions on genuinely-additive picks + the
SEAM-COMPILES brace-level verification — never feature logic, never new
behavior. Gates: auto-port only when the Watch delta is small and clean
(above), else wait for Alexey; backup ref FIRST (item 1); port-seam evidence = pr-checks GREEN (modum retired 2026-08-28);
every fixup commit carries the COMPILER'S OWN Session-Id trailer (+
`[role-exception]` tag on seam splices); disclosed in the next report + ledger.
Anything beyond a port seam → editor work (Step 2 hand-back rule).
