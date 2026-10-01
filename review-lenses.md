# review-lenses.md — Duty-6 reviewer lens catalog

Full briefs for the eleven Duty-6 review lenses (A–J + standing brain-scrub; regrouped v0.4.81 with C joining TOOLS and D sole in ARTIFACTS — H later joined D in ARTIFACTS, v0.4.113/115; the MECHANICAL family + Reviewer J added v0.4.161 on owner order). The Duty-6 method — read-only sub-agents, verbatim-quote verification, `oc-review-persist`
persistence, poll triple-check, verdict table — is canonical at `docs/instruments/review-rotation.md`
(meta-factory repo, not resolvable from this tree). This file owns the per-lens scope briefs
(brain-scrub brief lives at `review-lenses.md § STANDING LENS: brain-scrub`). Letters keep chronological
birth order (stable report/persist keys, not an ordering). Reviewer-performance
loop lessons fold INTO these briefs at ship time (ship-time fold, §FAMILY: META),
attributed to the reviewer that produced the evidence. Family identity is the
OBJECT under review, not the evidence flow between lenses (regrouped v0.4.81:
C joined TOOLS — gaps/shape/implementation pipeline; D is sole in ARTIFACTS,
the family IS the deletion owner gate). Membership and grouping change only
on census evidence + owner word (ship-time fold, §FAMILY: META).

#### FAMILY: DOCS — role files (wording / reading load / organization)

   - **Reviewer A — REDUNDANCY + ONTOLOGY:** same rule stated twice across
     files; duplicated war stories; terms violating the SKILL.md test ontology
     (SMOKE TEST / CODE TESTS / FEATURE-PRESENCE CHECK / EXECUTION SANITY
     SIGNAL); undefined coinages; stale ref names — INCLUDING every cross-repo
     pointer (`hq.md` §Duty 4/6, `docs/instruments/*`): resolve each named
     path/verb against this tree and against its declared home before calling it
     consistent (lens I-2.2 v0.4.116: A owns ref CONSISTENCY; B weighs refs only
     as load-weight — first finder gets attribution); SEDIMENT — stale layers
     that survive because adding feels safe and removing feels risky
     (docs-lens vocabulary reference:
     `skills/writing-for-agents/SKILL.md`). PLUS the churn-drift checklist, EVERY
     lens-A pass: (a) ONE CONCEPT = ONE NAME — sweep for synonyms of the same
     gate/tool/artifact; (b) GLOSSARY CONFORMANCE — every load-bearing term
     in a rule must resolve in SKILL.md §Glossary or §Test ontology;
     (c) POST-MIGRATION PATH SWEEP — after any artifact/path migration grep
     the ROOT literal of the OLD location (not the artifact name) across all
     three skill files; (d) ENUMERATION CONSISTENCY — counts of lenses/tools/
     gates/phases in prose must match their defining sections; (e) RETIRED
     CONCEPTS MARKED — any mention of a retired role/tool carries
     RETIRED + date, never present-tense; (f) LEADING-WORD COLLAPSE — prose
     restating one quality across a phrase list or spelling the same idea
     out at 2+ sites collapses into a single pretrained leading word; a
     restatement is duplication wearing prose. PLUS PROVENANCE SEDIMENT:
     live rule text carries the RULE, never its biography — owner-directive
     parentheticals, incident dates, "first pass shipped ..." notes,
     STRENGTHENED markers move to CHANGELOG.md at ship time; a lens finding
     names each offender.
   - **Reviewer B — LLM EFFICIENCY + RESPONSIBILITY CREEP:** token weight of
     each role's required reading (a worker must not need another role's
     procedures), prose that should be tables, dead references, duties
     migrating across HQ/Editor scope lines (Compiler archived).
     PLUS the NO-OP TEST sentence by sentence (docs-lens vocabulary
     reference: `skills/writing-for-agents/SKILL.md`) — a line the model
     already obeys by default is load paid for nothing (does it change
     behavior vs the default? the fix is a stronger term, not a longer
     sentence); reference that belongs behind a context pointer to a linked
     file instead of inline (progressive disclosure — the information
     hierarchy: in-skill steps with checkable completion criteria, in-skill
     reference, external reference); and SPRAWL — a file too long even when
     every line is live and unique (cure: disclose reference, then split by
     branch — not word-trimming).
     PLUS the CACHE test (vocabulary refresh 2026-09-10, upstream
     writing-for-agents f054def): the environment is a source of truth too
     (config files, scripts, directory layout, --help) and a document that
     restates it is a cache — a copy of a lookup earning its load only when
     the lookup is expensive; cache what the agent cannot find by looking
     (the unwritten convention, the reason behind a choice, the gotcha no
     config confesses), leave one-file/one-command lookups to the
     environment where they cannot go stale.
     PLUS the NEGATION test (vocabulary refresh 2026-09-10): steering by
     prohibition drags the forbidden behaviour into context and makes it
     more available (the ban half-reads as an instruction to do the thing);
     flag prohibitions that restate a positive target already present, and
     require the positive phrasing ("write one-line comments", not "don't
     write essays") — a prohibition earns its place only as a hard
     guardrail phrased positively alongside.
     PLUS the ONE-TRIGGER-PER-BRANCH pointer test: a context pointer's
     branches are the distinct cases that reach the material; synonyms
     renaming one branch are one branch written twice — collapse them.
     PLUS the SUBSUMED PROCEDURE PRUNING RULE (v0.4.182): when a composite or
     milestone tool ships (e.g. `oc-start`, `oc-ship-chain`, `oc-smoke`),
     lower-level step-by-step plumbing rituals (manual worktree manipulation,
     manual `oc-prchecks` loops, manual issue log comments, manual push to main,
     manual log formatting) must be aggressively pruned from role files.
     Role files must document only the single milestone invocation and its
     recovery semantics, not internal plumbing procedures the tool handles.
   - **Reviewer G — ROLE-FILE STRUCTURE:** the ORGANIZATION of EACH role file
     — the role files (re-derived from `ls *.md` at spawn time; count not
     hardcoded — lens G-F8 v0.4.89) plus every
     split-out reference page in the skill root, re-derived from `ls *.md`
     at spawn time (objects rot, the dimension doesn't) — phase/duty ordering vs actual
     work sequence, sections grown past cohesion (one section = one concern),
     rules living in the wrong section, cross-reference integrity after
     edits, whether a file should split (e.g. per-phase reference pages) or
     regroup. Every STEP in a role file must end on a CHECKABLE completion
     criterion (can the agent tell done from not-done? vague criteria invite
     premature completion). Before any split verdict, test the cheaper
     ladder moves first: disclose reference behind a context pointer, regroup
     for CO-LOCATION (a concept's definition, rules, and caveats under one
     heading). Findings must weigh the cost of a split (cross-refs, worker
     reading load) against the cost of growth.
     PLUS the EXPLORATION & DRY VERIFICATION GATE (v0.4.182): every code-producing
     role file (e.g. `editor.md` Phase 3) MUST explicitly mandate structural symbol
     exploration (`memory_search scope="external"`) and DRY verification before
     editing or writing code. Flag any exploration phase that permits blind code edits
     based on literal text grep alone without symbol-graph, caller-tree, and
     shared-abstraction analysis.
     LOAD-PATH MANDATE: any split or regroup verdict
     MUST also trace the skill's LOADING — which parts are always-injected
     (AGENTS.md anchors) vs on-demand (`load_brain_file` / SKILL.md section
     loads) — and verify every moved section remains reachable on the paths
     its readers actually use: the anchor line still points at the new home,
     the post-compaction re-load hint still names a file that holds the rule,
     and nothing a role loads by habit (HQ duties, editor phases)
     lands only in a file that role never opens. A split that breaks the
     load path is a REGRESSION finding against itself, not a cleanup.

#### FAMILY: MECHANICAL — the law corpus read against on-disk state (enforceability class)

   - **Reviewer J — MECHANICAL ENFORCEMENT (law that should be a tool):** the LAW
     CORPUS itself — `SKILL.md`, `fleet-directives.md`, `editor.md`,
     `harvest.md`, `hq.md`, `triage.md`, `toolsmith.md`,
     `tools/docs/RC-CONTRACT.md` — read as a specification of WHO DECIDES, and asked of
     every rule: **is this decision a pure function of state on disk?** If it is, the
     rule is a TOOL SPEC THAT HAS NOT BEEN WRITTEN YET and the finding names the tool
     half. Owner principle (2026-09-12, verbatim): *"that should be purely
     mechanical"* — law must not assign to an agent any decision a tool can settle
     from the tree, the ledger, the journal, git, or an API.
     THE TEST — quote it in every report:
     **T1** the decision is a pure function of state on disk (no human judgement, no
     owner taste) · **T2** a tool already touches that state, or an existing tool is
     the natural host · **T3** the rule currently asks an AGENT to remember, derive,
     or re-check that state by hand. **T3 is the tell:** a rule phrased as an
     instruction to a reader (*"always verify…"*, *"never forget to…"*, *"run X
     before Y"*, *"re-derive the set"*) is the defect class. Failing T3 = already
     mechanical, the prose is descriptive, NO ACTION. Failing T1 = a GATE
     (owner/design/verdict) and prose is its correct home — automating it would
     delete the human, which is the point of the gate; a gate is NEVER a J finding.
     EVIDENCE FORMAT — each finding carries (a) the law site, file + verbatim quote,
     (b) the state the decision reads, (c) the tool that should own it and its
     single-command interface, (d) the cost already paid (incident, ledger row, run
     id) or the word `unpriced`. A finding with no (c) is not a finding — it is the
     rule restated in other words, and HQ REJECTS it.
     THE STANDING EXEMPLAR (the finding that created this lens): the docs-only LEG1
     exclusion set — law shipped a 21-path snapshot PLUS a `grep` telling a lane to
     re-derive it, i.e. agent memory as a gate input. Amended v0.4.161 so the TOOL
     derives the set at gate time and the paths are illustrative only; the tool half
     is defect #20.
     NOT THIS LENS — whether a law-cited verb or flag EXISTS on the tool it names
     (the phantom-verb class: `--resume`, `stamp proposal`) is a corpus LINT (audit
     M2-18, Toolsmith), not a reviewer pass; J does the class no lint can decide: is
     the decision state-derivable at all, and where does the tool half belong.
     BOUNDARY vs C — C owns recurring multi-step PROCEDURE rituals that should
     collapse into one command; J owns law TEXT whose single decision is
     state-derivable, including one-shot checks and any set or list a lane is told to
     hold in context. One site, one lens: object is law text → J; object is a
     procedure → C.
     BOUNDARY vs D/H (v0.4.162, from I-7.1) — the ARTIFACTS family owns the
     ARTIFACT and its verdict: D asks what still reads or writes a file, flag or
     marker, H asks whether the ledger's own record is coherent, and both end in an
     HQ poll triple-check + owner word. J owns the LAW SENTENCE that assigns the
     decision. So a rule telling a lane to look up whether an artifact is still
     referenced is J's finding — the lookup is state-derivable and belongs in a
     tool — while the DELETE / ARCHIVE / KEEP verdict stays D's. One site, one lens:
     object is an artifact on disk → D/H; object is law text whose decision is
     state-derivable → J.

#### FAMILY: TOOLS — the tools/ surface (gaps / shape / implementation)

   - **Reviewer C — CLI-AUTOMATION + USAGE GAPS:** recurring multi-step MANUAL
     rituals in
     any role's procedure that are deterministic enough to be one CLI command
     (state-file sealing, presence gates, checksums, roster pulls, receipt
     delivery). Each finding names the proposed tool + its single-command
     interface. EXCLUDES: one-off steps, human-judgment calls (approval
     gates, smokes), anything already a gate. Candidates feed the
     HQ's process-tool ownership (scope above). PLUS USAGE-LOG
     ANALYSIS: every C pass reads the actual tool records — state-dir
     `tools.log`, `oc-deploy/journal/*.jsonl`, `workers-ledger.json` events,
     smoke-verdicts — and derives ground truth no prose review can: which
     verbs/flags are really invoked and how often, rc distributions (a tool
     whose calls cluster on rc 2 is a broken interface), documented tools
     never invoked in the window (YAGNI/deletion evidence for Reviewer D),
     hand-built ritual artifacts that a proposal should replace. Findings
     cite the log rows they rest on. ADOPTION-COMPLIANCE CHECK (v0.4.120,
     owner-ordered): every C pass samples runtime `Detaching '...'` records
     and flags ANY `gh run watch` / hand-rolled nohup CI poller spawn as a
     law violation (one-watcher law, editor.md) — official surfaces are
     native detached execution (`background: true`) and one-shot `gh run view`
     (for a blocking gate, `oc-prchecks --wait`); also flags
     `oc-prchecks --wait` used as a verdict waiter (double-duty). Each
     violation names the session id from the log row. Boundary watch vs A/B: C's dimension is
     GAPS (what should be a command), not doc wording or weight.
     BOUNDARY vs J (v0.4.161): C's object is a PROCEDURE carrying a recurring
     multi-step ritual; J's object is LAW TEXT carrying a single decision that is a
     pure function of state on disk — including one-shot checks and any set or list
     a lane is told to hold in context. One site, one lens; the two never both claim
     the same finding.

   - **Reviewer E — INTERFACE/TOPOLOGY:** the TOOL SURFACE itself — pairs of
     tools whose invocations are bound to come one after another in practice
     (merge candidates), verbs that belong in one tool instead of two, a flag
     duplicating another tool's job, a ritual two tools cover in half each.
     Lens A reviews duplicate RULES; E reviews duplicate/chainable INTERFACES.
     Each finding names the merge/verb-move + its single-command shape.
     EXCLUDES: one-off chains, anything with an approval gate between the
     steps (a gate is human judgment — never merged away).
     STANDING EXTRA: E also reviews the
     upstream-drift census surface (`oc-upstream-delta` patrol output) for
     silent drift — the next merge window must never start blind.
   - **Reviewer F — TOOL CODE REVIEW:** the tools/ implementations themselves
     — shell correctness (quoting, set -e gaps, rc collisions with the
     documented rc register), journaling completeness (every state-changing
     step writes its log line BEFORE the next step — owner tool-logging
     rule), selftest coverage vs the documented interface, dead flags/verbs,
     divergence between SKILL.md tool-table rows and actual behavior (flags,
     rc, paths). Findings cite file:line. Fold of ruling n=2265 (v0.4.127
     ACCEPTED): the F adoption check also covers Duty-4 notify-brief quality
     (no separate lens).

#### RULE BLOCK: SKILL.md size budget — NOT a family (no lens of its own; Reviewer B enforces it)

   - **SKILL.md BUDGET RULE:** SKILL.md is the always-loaded router — every
     line costs Nx, where N is the role count in the STEP ZERO table — five since
     the v0.4.250 harvest carve-out — and each role re-reads it IN FULL under the RELOAD LAW.
     It carries: hard rules, ontology/glossary, tool-table PURPOSE-only rows,
     role routing, load paths. Executable procedure, verb vocabularies, and
     step-by-step mechanics belong in the owning role file or reference page
     (tools/docs/RC-CONTRACT.md = SOLE tool register). Every Duty-6 pass re-weighs
     SKILL.md against this rule; growth beyond router scope = findings.

#### FAMILY: ARTIFACTS — files, state, ledgers, flags (deletion verdicts — the family IS the owner gate; C usage-log YAGNI evidence feeds it from TOOLS; BOUNDARY vs J, v0.4.162 — this family owns the ARTIFACT and its verdict, J owns the law sentence that assigns a state-derivable decision: object is an artifact on disk → here, object is law text → J)

   - **Reviewer D — DELETION SAFETY:** enumerate retired / stale /
     duplicate-looking artifacts in the skill scope (files, state files,
     ledgers, markers, tool flags) and for EACH list what reads or writes it
     (grep tools/, crons, skill files, journal vocabulary), then classify
     DELETE-SAFE (evidence law, folded from D's own method note v0.4.116:
     a zero-hit claim from a |-pattern grep in literal mode is UNVERIFIED —
     quote the query + scope for every negative-existence claim) / ARCHIVE / KEEP with that reference list as the evidence. **The reference enumeration is a TOOL-HALF wherever a tool already computes it** (J's T2 boundary — `oc-health` classes 4/18, `oc-claims-single-source`, `oc-watcher-audit`): NAME the tool and its command rather than hand-grepping, and where NO tool covers a class, say so and propose it. A hand grep held in a reviewer's head is agent memory as a gate input, which is the defect J exists to find.
     "Looks stale" is a hypothesis, never a verdict. Nothing deletes without
     HQ's poll triple-check + owner word.
   - **Reviewer H — LEDGER HEALTH (shipped v0.4.114, owner GO 2026-09-08 20:16Z):**
     the workers-ledger.json read AS A WHOLE, not per-slice — the slice tools
     (`oc-ledger claims`, `oc-ship-audit`) each audit one family and stay the
     enforcement surface, while the `oc-roster-detached-sweep` cron sweeps
     detached work; H reads for what they cannot
     see: (1) RECEIPT COMPLETENESS — incident/lesson-mention rows with no
     corresponding codified rule in fleet-directives.md/editor.md/AGENTS.md
     (lesson-extraction completeness; each finding names the row AND the law
     home that should carry it, or the explicit owner waiver), (2) PHANTOM
     FAMILIES — rows claiming stamps/writes/deliveries with no same-turn tool
     receipt verifiable from the row's own citations (the n=1845/n=1555 class),
     (3) CLAIM LIFECYCLE — open claim-refs whose chains closed (merged/shipped/
     retracted) without a release row, (4) CONTRADICTION PAIRS — later rows
     asserting the opposite of earlier rows for the same object without a
     retraction, (5) CADENCE/VERSION SYNC — skill-bump rows vs tags vs
     CHANGELOG monotonicity. Evidence format unchanged: every finding cites
     the ledger row n + the verifiable artifact (git/gh/log) that confirms or
     breaks it — quote-or-no-finding. H reviews the JOURNAL, never edits it;
     corrections land as new rows or law edits via HQ.

#### FAMILY: META — review machinery and catalog (added v0.4.114)

   - **Reviewer I — META-REVIEW:**
     reviews the LENS CATALOG AND ITS OUTPUT — the only reviewer whose object
     is the review machinery itself. Scope: (1) BRIEF CORRECTNESS — each brief
     in this file (A–J) still matches what its reviewer actually checked in
     the latest persisted report (scope drift, stale check classes), (2)
     OVERLAP — findings double-covered by two lenses, or coverage GAPS where
     no lens owns an artifact class, (3) FALSE-POSITIVE/NEGATIVE HISTORY —
     the retraction/rejection rows in `workers-ledger.json` (query:
     `grep -i 'retract\|reject'`) plus the ship-time folds already in these briefs
     (precedents: brain-scrub "cargo ban homeless" overstatement, the
     B-8 misattribution — both rejected 2026-09-08; later retractions are
     recorded in the ledger and MUST be folded in at ship time, e.g. the
     boot-instant arithmetic corrected against bytes at `n=449`), (4) CATALOG HYGIENE —
     counts in prose must match their defining sections; the family map must
     match the briefs; retired lenses marked RETIRED + date; (5)
     MECHANICAL-VS-MEMORY — J's T1–T3 applied REFLEXIVELY to the catalog's
     own assignments. EVIDENCE DISCIPLINE rides the same quote-or-no-finding
     rule stated below (I-4.1 v0.4.116 evidence unit: locator + verbatim
     snippet for HIGH/P-class; locator-only permitted for mechanical nits;
     volatile files cited by section header + short quote, line numbers
     secondary — I-4.2).
     CORPUS (I-5.1 v0.4.116): durable reports live in
     `reviews/<cycle>/reports/`; when two skill-review-index.log files
     diverge, defer to `tools/state/oc-review-persist check-cycle` (contract: `docs/instruments/review-rotation.md` §step-0 recovery): the canonical root is the STATE repo
     (`$OC_DEV_STATE/reviews/<cycle>/reports/`); the frozen skill-repo `reviews/` root is history and
     MUST NOT be written. Severity scale:
     HIGH (load-bearing lie / stall class) · MED (real gap, bounded blast
     radius) · LOW (nit). I reads
     persisted reports + this catalog + HQ's validation notes; it
     does NOT re-litigate findings already triple-checked, it audits the
     PATTERN. Output feeds catalog brief edits and reviewer spawning. Same
     quote-or-no-finding evidence rule. Self-reference cap: I may flag its own
     brief's defects, but never reviews its own report (recursion capped at
     one level).

#### STANDING LENS: `brain-scrub` — OUTSIDE the A–J families

*(Heading shape note, lens I F7 v0.4.206: this brief sat at `####` — the FAMILY level — with no family claiming it, so a cold reader could not tell whether it belonged to META or was a family of its own. It is neither: the rotation is `A–J + standing brain-scrub` (this file's lens list), the family map stays A–J, and this lens owns its own report. Registered in `oc-review-persist` LENSES as `brain-scrub`.)*

Standing lens in the Duty 4+6 skill-review rotation (registered in `oc-review-persist` LENSES). Scrubs the ops profile's brain files for opencrabs-dev process content living outside the skill:

1. **AGENTS.md** carries only one-line pointers + always-loaded anchors for dev-process law — a full law text duplicated here is a finding (canonical home is this file; one concept, one home).
2. **MEMORY.md** carries no discipline laws — passive memory never binds on a cold session (shipped template law); directives found there are findings.
3. **Every finding lands as a move-with-verification:** the canonical copy is verified present in the skill BEFORE anything is removed from the brain file. Brain files are append-only — shrink/cleanup requires explicit owner approval and `dedup_intent`/`cleanup_intent`.

Reports persist via `oc-review-persist brain-scrub <text|@file>`. Same mechanics as every other lens: verdict consolidated → stamped (the cadence-stamp law at `hq.md §Cadence boundary is stamped at review consolidation` applies unchanged — the close form is `oc-ledger stamp note "v<version> ACCEPTED"`, NOT `review-battery`, which does not reset the counter).
