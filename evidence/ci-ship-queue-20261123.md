# CI Ship Process — Toolsmith work queue (steps 3, 4, 5, + #160)

**Owner:** HQ (`0117dd29-5f4b-4184-9bf4-d19dc74ac266`). **Lane:** Toolsmith (`2fae1230`).
**Plan:** "Fix CI Ship Process" (approved session plan). **Evidence note:** `evidence/ci-ship-inventory-20261123.md`.

Step 2 (`factory#156` — the ledger write path) is **already claimed and in flight** in this lane.
This file carries the REST of the queue. One brief, four work orders, sequenced — do not start a
later one before the earlier one lands, because #158 consumes #157's format.

---

## Standing constraints (every order)

- **NO local `cargo` / `rustc` / `clippy`** — CI is the only compile gate.
- **NO live build, swap, daemon restart or deploy** in this work. Use gh shims, fake carriers,
  isolated `OC_DEPLOY_STATE_DIR`.
- The battery is **serialized** (15–20 min). Do not run a competing battery; accept a green
  receipt only if the tree did not change mid-run (`tools/tests/battery-last.json` carries the
  tree fingerprint).
- **Issue-first**: a discovered defect gets a factory issue filed before fix work.
- Commit trailers: `Session-Id: <yours>`; code commits carry
  `Issue-Ref: leshchenko1979/opencrabs-dev-factory#<N>`.
- **Positive control per order** (fleet house pattern, `negctl-34-mutation-guard.sh`): a
  control that the mechanism actually fires, plus the suppression arms. Without the control every
  "never does X" arm passes on a tool whose X never executes at all.

---

## Order 3 — `factory#157` — durable gate receipt

**Deliverable:** a durable receipt file per gate run, naming the tested sha.

**Schema** (the amended issue body is authoritative; §F of the evidence note carries the
measurement that amended it):

| field | source | note |
|---|---|---|
| `schema` | constant | versioned so a reader can tell shapes apart |
| `requested_sha` | the dispatch's input | what was asked for |
| `tested_sha` | **`oc_job_sha`** (`lib/oc-patch.sh:36-43`) | NOT `oc_decode_job_sha_any` — see #160 |
| `pinned_sha` | the gate's **adoption pin** (`oc-gate:109`) | NEW: the sha the gate actually adopted |
| `carrier_ref` | dispatch input | |
| `carrier_head` | the carrier branch HEAD | **distinct** from `tested_sha` |
| `run_id` | gh run id | |
| `jobs[]` | per job: `name`, `conclusion`, `blocking` | `blocking` = the job that decides the verdict |
| failure detail | the per-step detail already parsed for tiebreaks (`oc-gate:61`) | |
| `verdict` | GREEN / RED / the refusal vocabulary | |
| `ts` | write instant | |

**Rules**

1. **Atomic write** (tmp + `mv`).
2. Written on **every** verdict, RED included — a RED run that leaves no receipt is
   indistinguishable from a gate that never ran.
3. `tested_sha` and `pinned_sha` **must agree**; if they differ, the receipt describes a
   different run than the one adopted → **fail closed**, do not write a passing receipt.
4. `tested_sha` MUST come from `oc_job_sha`. The any-shape decoder returns EMPTY on the five
   real mode-suffix shapes (order 6 / #160).
5. Path: under the **state dir**, named for the run id, resolved by the SAME resolver the ledger
   uses (one resolution, not two).
6. **Control arms**: (a) positive control — a receipt exists and names the sha; (b) no run → no
   receipt; (c) RED run → receipt written with the RED verdict; (d) pinned ≠ tested → no passing
   receipt; (e) a second run → a second receipt, the first untouched.

---

## Order 4 — `factory#158` — ship CONSUMES the receipt

**Deliverable:** the ship path stops re-deriving identity and reads the receipt.

1. `oc-ship` currently re-derives identity independently at `:1411`, `:1443-1450`, `:1458-1459`,
   `:1496-1498`. It must read the receipt instead.
2. The receipt's `tested_sha` must match the `--gated-sha` the ship was given → else **fail
   closed**.
3. **`oc-audit-ship:242`** is in scope too (evidence note §G): it selects the build job by
   `name contains sha AND NOT contains("ORDER gates")` — the same question the receipt answers.
   It should read the receipt, not form a second opinion from the same job names.
4. The **docs-only skip** (`oc-ship:1385-1400`) must journal its reason and claim **no** receipt.
5. **Control arms**: a receipt naming a different sha → no ship; a missing receipt → no ship;
   a RED receipt → no ship; a GREEN receipt → ship proceeds.

---

## Order 5 — `factory#159` — the one-commit path, PROVEN

**Measured (§C): the premise of this order was false — there is nothing to relax.**
`oc-ledger sync`'s gates (`oc-ledger:1713-1721`) are **content** checks on files
(`grep -Eq "^version: $v$" SKILL.md`, `grep -Eq "^## v$v([ —(:]|$)" CHANGELOG.md`), and the commit
leg (`:161-184`) no-ops on a clean tree via the #467 `git diff --cached --quiet` guard. **The
one-commit path already works.**

**Deliverable — therefore a PROOF, not a relaxation:**

1. A **battery leg** that stages the docs + the version bump together and asserts a single commit
   + `oc-ledger sync` passes. No gate is deleted, relaxed or reordered.
2. HQ owns the prose (`SKILL.md`, `CHANGELOG.md`, `hq.md`, `editor-ship.md`) — **Toolsmith does not
   touch skill markdown**. Hand the leg over and HQ writes the words.
3. Record in the report: what the leg proves, and that no gate changed.

---

## Order 6 — `factory#160` — the job-name decoder gap (NEW, filed from the inventory)

**Defect:** `oc_decode_job_sha_any` (`lib/oc-embed.sh:35-41`) returns **EMPTY** for
`PR-lane gates (<sha> — FIX MODE)` — its fallback regex requires the sha to be **immediately**
followed by `)`, and the carrier puts a mode suffix between them
(`ci-lane-impl.yml:401`; five real shapes: FIX MODE · LOCK REGEN · LOCK UPDATE · SWAP MODE · FAST).

**Measured blast radius:** in a **gate-mode** run the build job is SKIPPED (its name renders as
the literal placeholder, `oc-verify-artifact:249`) and `ORDER gates` belongs to build mode — so
`PR-lane gates` is the ONLY sha-carrying job. With a suffix: `oc-verify-job` → rc 4 REF-MISMATCH,
`oc-verify-artifact` → rc 4 PROVENANCE, `oc-fanout` → empty sha → unattributable range (the #932
symptom class). **Fail-closed, not wrong-write.**

**Fix requirement:** the any-shape decoder must accept a sha followed by a suffix inside the same
parentheses. `oc_decode_job_embed` stays **two-field-only** — its contract is load-bearing.

**Required arms:** positive control (the suffix shape decodes) · the bare form still decodes · the
two-field embed still decodes · the two-field-only decoder still REFUSES the bare form (the
existing `run.sh` section 00b contract) · a no-sha shape still decodes empty · **`oc_job_sha` and
`oc_decode_job_sha_any` AGREE on every real shape** — the durable one, because the fleet has two
predicates for one question and they disagreed on a production shape.

---

## REPORT BACK

For each order: commit shas (pushed, remote-verified), the battery line (`PASS: N FAIL: 0`, rc,
wall, receipt path, tree fingerprint), what shipped, **what you did NOT change**, and anything you
found that is not in this file. Cite a factory issue number for every code commit.
