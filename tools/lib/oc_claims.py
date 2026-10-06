#!/usr/bin/env python3
"""oc_claims.py — THE canonical claim-closure predicate (issues #305, #313, #314).

ONE implementation, imported by every tool that asks "is this claim still open?".

WHY THIS FILE EXISTS. Four copies of this predicate had drifted apart across
`oc-harvest-dispatch` (#305), `oc-issue-dispatch` (#309), `oc-roster` and
`oc-ledger` (#313). They did not merely differ in style:

  * two copies extracted issue tokens as INTEGERS, two as STRINGS, and each
    compared tokens against its own type — so on a ledger mixing both, one
    copy's `tok in e['tokens']` was silently always-False (a claim could never
    close) while another's was silently always-True-able;
  * only one copy asked WHO authored the closing row. The others treated any
    lane's closing event that merely MENTIONED `#N` in prose as closing every
    lane's claim on `#N` — which reported an ACTIVE lane as IDLE and bypassed
    the in-flight fencing that stops a patrol double-dispatching live work
    (#305);
  * conversely, a CROSS-LANE standdown addressed to `#N` (`STANDDOWN #269
    (52058a75)`, stamped by Triage) closed nothing at all, so a shipped,
    stood-down claim stayed OPEN until its claimant hand-stamped a redundant
    closure row (#313, live row n=7803 / n=8055).

Import from a tool (bash-embedded python included):

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'lib'))
    import oc_claims as oc

THE CANONICAL RULE — a claim on `#N` is CLOSED by a LATER event whose kind is
in CLOSING_KINDS and which satisfies ANY of:

  1. it is authored by the SAME lane as the claim, and references `#N`; or
  2. it is ADDRESSED to `#N` — its `what` begins `#N` (optionally after the
     `STANDDOWN ` keyword). Administrative sweeps
     (`#N — closed-issue stale claim sweep`) and a lane's own `#N COMPLETE`
     rows take this form, and their author is by design NOT the claimant; or
  3. the claim's author is UNATTRIBUTED (the `(unattributed` /
     `unrostered-actor` sentinels) — there is no actor to discriminate on, so
     ANY later closer referencing `#N` closes it.

Signal 2 is deliberately NARROW: `what` must BEGIN with the reference. A
foreign lane's closing row that merely mentions `#N` in prose — `UNCLAIM #264 —
stood down in favour of editor lane X` — must NOT close another lane's claim.
That row releases its AUTHOR's own claim, and by naming X it in fact confirms X
still holds it (#305).

NO REGEX OVER `what` AS A WHOLE. Issue references are extracted by TOKEN, never
by substring and never by "first run of digits": a date (`2026-09-15`), the
owner handle (`leshchenko1979`), a commit sha or a session-uuid prefix must not
be read as an issue number (#272), and `claims 76` must not match a claim on
`#760` (c6b1a539 residual).

WHAT A CLAIM CLAIMS (#329). Reference extraction answers TWO different
questions, and one token list must not serve both:

  * "does this row REFERENCE `#N`?" — every HOME-space reference counts. A
    closing row's prose mention of `#N` is part of signal 1 (same author,
    references `#N`), so :func:`issue_ref_tokens` deliberately keeps them all —
    all of them that name one of our issues. A reference qualified by a
    repository we do NOT own is foreign and is skipped in BOTH predicates (#379,
    widened to :data:`HOME_REPO_SLUGS` by v0.4.284).
  * "does this row CLAIM `#N`?" — only the row's ADDRESS counts. A `what` is a
    SENTENCE: the issues it cites while explaining itself are context, not
    claims. Live instance — row `n=8226` claims #327 and its note ends `...
    one proven live break (#323)`; reading that mention as a claim registered a
    PHANTOM claim on #323, which then made `oc-ledger sweep-closed-claims` want
    to write a false unclaim row and made `oc-issue-dispatch` report an OPEN
    issue as taken. 13 such phantoms existed fleet-wide.

:func:`primary_issue_tokens` is that second predicate: the leading reference
CLUSTER — starting at the first reference and continuing while further
references are joined only by list punctuation (`,`, `/`, `+`, `&`) or
whitespace. Prose separates, list punctuation does not, so a genuine
multi-issue claim survives (`CLAIM #193, #205 — harvest packaging`) while a
citation in the body drops out. Measured over the live ledger: of the 37 claim
rows carrying more than one reference, 35 change target under this rule, NONE
becomes target-less, and the one deliberate dual claim is preserved.

NEW ROWS CARRY THE ANSWER. `oc-ledger claim`/`stamp claim` records the targets
as a structured `issues` array on the row, so a claim written from now on is
never re-derived from prose at all; :func:`primary_issue_tokens` is the
fallback for rows written before that field existed.

CLAIM FOOTPRINT (#307). The ledger raises a SECOND question alongside closure —
"which FILES does the claimed work touch?" — and that answer had drifted into
two more unanchored copies (one in `oc-harvest-census`, one in
`oc-harvest-dispatch`). Both resolved it by grepping commit messages for the
bare text `#N` (`git log -n 10 --grep=#N` in one, a substring test over
subjects and trailers in the other), so a commit whose PROSE merely mentioned
`#N` was read as work on `#N`. Closure and footprint are different questions
with different predicates; this module owns both, so a fifth and sixth copy
cannot appear. Footprint is anchored to the `Issue-Ref` TRAILER — the
machine-written link `oc-commit` derives from the actor's ledger claim — and
scoped to HOME space: see :func:`resolve_issue_commits`.

READ-ONLY. This module never writes the ledger; the sweep's write path lives in
`oc-ledger` and goes through the sanctioned `stamp` verb.

WRITE-TIME CONSUMER. `oc-ledger`'s own `_issue_ref_tokens` shell helper now
delegates here rather than carrying a fifth copy of the pattern. That one sits
on the WRITE path (`stamp claim`'s dead-letter guard, and `claim-ref`, which
derives an issue from the very text `claims` scans), so a drifting copy there
does not merely mis-report — it lets the tool write a claim the scanner cannot
see, or derive an issue the scanner never wrote. Agreement is the point.
"""

import datetime
import json
import os
import re
import subprocess

#: The 24h feature soak window, in seconds — THE single source for both the
#: refusal predicate and the expiry that predicate prints. Two spellings of the
#: same window (a `24.0` here, an `86400` there) drift the moment one is tuned.
SOAK_SECONDS = 24 * 3600
SOAK_HOURS = SOAK_SECONDS / 3600.0


#: The canonical workers-ledger.json location. ONE spelling for every reader:
#: the same precedence `oc-ledger` uses on the write side (OC_LEDGER, then
#: OC_DEV_STATE, then the ops profile default), so a reader can never look
#: somewhere the writer does not write.
def default_ledger_path():
    state = os.environ.get("OC_DEV_STATE") or os.path.join(
        os.path.expanduser("~"), ".opencrabs", "profiles", "ops", "opencrabs-dev")
    return os.environ.get("OC_LEDGER") or os.path.join(state, "workers-ledger.json")


def load_ledger(path=None):
    """Read + parse the workers-ledger. Raises OSError/ValueError -- loud, never
    a silent empty ledger: a caller that cannot tell "no claims" from "no file"
    reports an idle fleet for a broken path.
    """
    with open(path or default_ledger_path()) as fh:
        return json.load(fh)


def fmt_iso_ts(ts):
    """A unix timestamp as ISO8601 UTC, or ``none`` when unresolved.

    ``ts <= 0`` renders as ``none`` and never as 1970-01-01: an unresolved
    anchor is a fact the reader must see, and an epoch date hides it behind a
    plausible-looking deployment time.
    """
    if not ts or int(ts) <= 0:
        return "none"
    return datetime.datetime.fromtimestamp(
        int(ts), datetime.timezone.utc).isoformat()


def soak_anchor_fields(anchor_commit, anchor_ts, basis="swap"):
    """The anchor quadruple carried by EVERY 24h-soak refusal (#415, #315).

    ``anchor_commit``/``anchor_deployed_ts`` name the instant the soak clock
    started and ``eligible_at`` is that instant plus the window — a schedule,
    so a refused lane knows WHEN to come back instead of reverse-engineering
    the anchor from the swap journals by hand (the defect a Duty-6 review
    routed here, 2026-09-19).

    ``soak_basis`` (#315) STATES the definition with the value: ``swap`` when
    the anchor is a deploy/swap-journal time, ``commit`` when no swap history
    resolved and the commit time was used instead (a DIFFERENT basis, whose age
    is an upper bound on the true soak age), ``unresolved`` when there is no
    anchor at all. Without it the no-swap fallback was labelled
    ``anchor_deployed_ts`` indistinguishably from a real deploy time, so a
    reader could not tell which basis produced the number.

    Rendering it in ONE place is what keeps ``eligible_at`` arithmetically
    equal to ``anchor + 24h`` at every refusal site rather than re-derived —
    and mis-derived — at each.
    """
    ts = int(anchor_ts) if anchor_ts else 0
    return "soak_basis=%s anchor_commit=%s anchor_deployed_ts=%s eligible_at=%s" % (
        basis, anchor_commit, fmt_iso_ts(ts),
        fmt_iso_ts(ts + SOAK_SECONDS if ts > 0 else 0))



def fmt_hours(h):
    """Hours at one decimal — the unit every soak message quotes."""
    return "%.1fh" % h


def classify_soak_anchor(commit_sha, commit_ts, resolve_fn, swaps, now_ts):
    """Resolve ONE soak anchor -> (state, age_hours_or_None, anchor_fields).

    THREE states, not two. ``resolve_fn(sha, ts)`` returns the deploy anchor or
    0, and 0 means EITHER "the deploy is genuinely just now" OR "nothing could
    be resolved at all" — collapsing the second into the first is the defect:
    ``age_hours = 0.0`` refused an unresolvable anchor while PRINTING A FALSE
    AGE and carrying no schedule, defeating the #415 triple's whole purpose.

    The legacy no-swap-history fallback is preserved: with an EMPTY swap
    journal the commit timestamp is the only anchor that exists, so it is used
    directly rather than reported as unresolved.

    Refusing on ``unresolved`` is kept deliberately — the failure is
    one-directional, and an anchor that cannot be resolved must never produce
    an APPROVE. The caller carries the class in its own verdict prefix, so rc
    does not change and no consumer breaks.
    """
    d_ts = resolve_fn(commit_sha, commit_ts)
    # #315: the basis travels with the value. A swap-resolved anchor is a DEPLOY
    # time; the no-swap-history fallback is the COMMIT time -- a different basis
    # that must be labelled distinctly, not rendered as anchor_deployed_ts.
    basis = "swap"
    if not d_ts and not swaps and not os.environ.get("OC_HARVEST_MOCK_DEPLOYED_TS"):
        d_ts = commit_ts
        basis = "commit"
    if d_ts and d_ts > 0:
        age_hours = (now_ts - d_ts) / 3600.0
        return ("fresh" if age_hours < SOAK_HOURS else "soaked",
                max(0.0, age_hours), soak_anchor_fields(commit_sha, d_ts, basis))
    return "unresolved", None, soak_anchor_fields(commit_sha, 0, "unresolved")


def soak_unresolved_note(commit_ts, now_ts):
    """Why an unresolved anchor carries no schedule, and what the commit date says.

    The commit timestamp is an UPPER BOUND on the true age, never an anchor:
    the content cannot have deployed before the commit existed, but it may have
    deployed at any point since — so a 19-day-old commit is NOT evidence that
    the 24h window has passed.
    """
    if commit_ts and commit_ts > 0:
        bound = ("the commit timestamp %s is an UPPER BOUND on the true age (%s old), "
                 "not an anchor -- its content may have deployed at any point since"
                 % (fmt_iso_ts(commit_ts), fmt_hours((now_ts - commit_ts) / 3600.0)))
    else:
        bound = "the commit timestamp is unreadable, so not even an upper bound is available"
    return ("no resolvable deploy anchor (not an ancestor of any journaled swap, and neither "
            "the patch-id twin nor the smoke anchor resolved it); %s; no eligible_at: there "
            "is no schedule to give until the anchor resolves" % bound)


#: The only event kinds that can close a claim (v1 vocabulary).
CLOSING_KINDS = ("close", "confirm", "reject", "done", "unclaim")

#: The kinds that are evidence the WORK LANDED. A strict subset of
#: CLOSING_KINDS, and NOT interchangeable with it — "closes a claim" and "the
#: fix shipped" are different questions (#337).
#:
#:   done   — the lane reported the work complete (smoke PASS verified)
#:   close  — the issue was closed
#:
#: The other three close a claim WITHOUT the work landing, which is why using
#: CLOSING_KINDS as a landing test starves real work:
#:
#:   confirm — `CONFIRM #N — claim verified live (workers[].confirmed=true)`:
#:             a bookkeeping flag is flipped; nothing shipped.
#:   unclaim — the claim is RELEASED (`#N — closed-issue stale claim sweep`,
#:             `#N — stood down`): the issue returns to the pool, unbuilt.
#:   reject  — the claim is REFUSED: no work was done at all.
#:
#: Measured over the live ledger 2026-09-18: CLOSING_KINDS reaches 228 issues,
#: 125 of them ONLY via the three non-landing kinds. 77 of those 125 are landed
#: work that a git-landed check catches independently; the other 48 are
#: reachable by `unclaim` ALONE (a released claim: `#N — closed-issue stale
#: claim sweep`), so a CLOSING_KINDS-based filter suppressed them purely because
#: a claim had been RELEASED while the work was still unbuilt.
#:
#: On today's data all 48 are already closed on GitHub, so this narrowing
#: changes NO dispatch outcome. It is a latent-correctness fix: the predicate
#: now means what its name says, and the next released-but-unbuilt issue is no
#: longer silently starved. (Do not claim a present-tense starvation without
#: re-measuring the intersection with the live open set — the first version of
#: this comment asserted three named issues were wrongly filtered and was wrong:
#: #248/#253/#268 each carry a genuine git-landed commit, and were correctly
#: skipped by the git arm, not by this one.)
LANDED_KINDS = ("close", "done")

# Accepted issue-reference forms: `#N`, `issue N`, `issue=N`, `issue#N`.
_REF_RE = re.compile(r"(?:#[0-9]+|issue[ \t=#]*[0-9]+)", re.IGNORECASE)
_DIGITS_RE = re.compile(r"[0-9]+")

#: The repos that OWN this box's issue space — every tracker the fleet files on
#: (two-stream routing, SKILL.md v0.4.284, owner order 2026-10-03). A reference
#: qualified by a slug INSIDE this set is OUR space and anchors normally; a slug
#: OUTSIDE it is foreign (third-party/upstream-other space) and must never fence
#: an issue here (#379).
#:
#: Before v0.4.284 this was a SINGLE fork slug, so a reference qualified
#: `adolfousier/opencrabs#N` read as foreign and was skipped. That was correct
#: while the fork was the only tracker — and is WRONG now, because that slug IS
#: the binary tracker, and a lane working a binary issue writes exactly that
#: trailer. The set, not the slug, is the discriminator.
#:
#: 2026-10-04 — the upstream repo was RENAMED `adolfousier/opencrabs` ->
#: `opencrabs/opencrabs`. The NEW slug is the canonical one lanes now write; the
#: LEGACY slug stays in the set because GitHub redirects it and refs written
#: before the rename must keep anchoring. Dropping the legacy slug would turn
#: every pre-rename binary-tracker ref into a #379 foreign-ref refusal.
HOME_REPO_SLUGS = (
    "opencrabs/opencrabs",                   # BINARY tracker (upstream, canonical)
    "adolfousier/opencrabs",                 # BINARY tracker (legacy slug; redirects)
    "leshchenko1979/opencrabs-dev-factory",  # FACTORY tracker
    "leshchenko1979/opencrabs",              # FORK (historical; PRs still land here)
)

#: The FORK slug specifically. On UPSTREAM (`adolfousier/main`) a bare `#N`
#: trailer names an upstream issue/PR, a DIFFERENT number space from the fork's,
#: so only a value SLUG-QUALIFIED with this slug anchors a fork issue there
#: (#356).
FORK_SLUG = "leshchenko1979/opencrabs"

#: The historical single slug. Still the meaning of an UNQUALIFIED `#N`: a bare
#: number is fork space, because that is the space the ledger's own rows were
#: written in before the split.
FORK_REPO_SLUG = "leshchenko1979/opencrabs"

#: `<owner>/<repo>` sitting IMMEDIATELY before a reference — the prose path's
#: repo qualifier.
_SLUG_BEFORE_RE = re.compile(r"([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)$")

def _is_foreign_ref(text, pos):
    """True when the reference at ``pos`` is qualified by a slug we do NOT own.

    `#379`: `_REF_RE`'s `#[0-9]+` alternative also matched the `#N` INSIDE
    `owner/repo#N`, and nothing on the prose path was repo-aware — so a row
    naming a THIRD-PARTY issue (`someorg/theirproject#1419`) registered a claim
    on fork issue 1419, which does not exist. It reported as an open claim for
    12.5 days (live carrier: ledger n=1678), listed under the lane's claims by
    `oc-roster classify`, and could never be closed by fork-side work. The
    trailer path already refused a foreign repository
    (:func:`parse_issue_ref_value`); this is the same refusal for prose.

    v0.4.284 widened the ownership test from ONE slug to :data:`HOME_REPO_SLUGS`,
    because the fleet now files on three trackers and a binary-issue trailer
    (`adolfousier/opencrabs#1901`) must ANCHOR rather than be skipped. The n=1678
    carrier is the live example of the change: it was a dead letter under the
    one-slug rule and is a legitimate claim on the binary tracker now. A slug
    OUTSIDE the set — `acme/widgets#7` — is still refused, and that is the #379
    protection the refusal exists for.

    The IMMEDIATE form only — `slug#N`, no space between. Measured over the live
    ledger's 18 181 prose fields, that form carried exactly two slugs
    (`adolfousier/opencrabs` 80x, `leshchenko1979/opencrabs` 65x) and the
    whitespace-separated form (`slug issue N`) never carries a foreign one, so
    the immediate form IS the whole live population. Tolerating whitespace would
    also read a filesystem path (`tools/lib/oc_claims.py issue 379`) as a slug
    and silently drop a real reference — a false negative in exchange for
    nothing.
    """
    match = _SLUG_BEFORE_RE.search(text[:pos])
    return bool(match) and match.group(1) not in HOME_REPO_SLUGS

# A claim's ADDRESS: consecutive references joined ONLY by list punctuation or
# whitespace. Anything else (prose, a separator, a bracket) ends the address and
# begins the body — see the module docstring, "WHAT A CLAIM CLAIMS".
_CLUSTER_RE = re.compile(
    r"^(?:[,\s/+&]*(?:#[0-9]+|issue[ \t=#]*[0-9]+))+", re.IGNORECASE)

# Actor forms observed live in the ledger's free-text `by` field:
#   'editor <uuid>', '<short-uuid>', 'editor-<short-uuid>',
#   'toolsmith/<short-uuid>', 'unrostered-actor <short-uuid>',
#   'editor lane (session <short-uuid>)', bare labels ('lamp-lane', 'supervisor').
_FULL_UUID_RE = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.IGNORECASE)
_SHORT_UUID_RE = re.compile(r"([0-9a-f]{8})(?![0-9a-f-])", re.IGNORECASE)
# NB: a single character class, NOT '[-:/]?'. The alternation form mis-parses
# 'editor-1a63f103' by consuming the uuid into the role and losing the identity.
_ROLE_PREFIX_RE = re.compile(
    r"^(unrostered-actor|editor|triage|supervisor|hq|toolsmith|carrier|lane)\s*[-:/]?\s*",
    re.IGNORECASE)

# Sentinels meaning "no resolvable actor" (see derive_by in oc-ledger).
UNATTRIBUTED_PREFIXES = ("(unattributed", "unrostered-actor")


def issue_ref_tokens(text):
    """Every HOME-space issue reference in ``text``, INTEGERS, first-seen order.

    Integers, not strings: the four drifted copies disagreed on this and one of
    them therefore compared a str token against int tokens forever-falsely.

    HOME space ONLY (#379, widened to :data:`HOME_REPO_SLUGS` by v0.4.284): a
    reference qualified by a repository we do NOT own (`acme/widgets#7`) is
    foreign and is skipped, exactly as :func:`parse_issue_ref_value` skips it on
    the trailer path. A reference on any of OUR three trackers — binary, factory,
    fork — anchors normally.
    """
    if not text:
        return []
    s = str(text)
    out = []
    for match in _REF_RE.finditer(s):
        if _is_foreign_ref(s, match.start()):
            continue
        for num in _DIGITS_RE.findall(match.group(0)):
            value = int(num)
            if value not in out:
                out.append(value)
    return out


def references(text, iss):
    """True when ``text`` references issue number ``iss`` (token match)."""
    return int(iss) in issue_ref_tokens(text)

def primary_issue_tokens(text):
    """The issue(s) a claim row CLAIMS — its leading reference cluster.

    Distinct from :func:`issue_ref_tokens`, which returns EVERY reference: this
    one answers "what is this row a claim ON?" and must not read a body citation
    as a second claim (#329 — see the module docstring).

    The cluster begins at the FIRST reference and extends while further
    references are joined only by list punctuation (`,`, `/`, `+`, `&`) or
    whitespace, so ``CLAIM #193, #205 — harvest packaging`` claims BOTH while
    ``CLAIM #327 — ... one proven live break (#323)`` claims only #327.

    Empty means "no HOME target" — which is NOT the same as "no reference
    anywhere", and the difference is deliberate (#379). A text whose LEADING
    reference is qualified by a repository we do NOT own returns ``[]``: the row
    leads with third-party work, and there is no issue of ours for it to claim.
    That is the existing dead-letter contract for a claim with no target, and it
    is the conservative direction — the alternative would hunt for a later
    reference and read a body citation as the address, which is the #329 phantom
    rebuilt from the other end. Before #379 the leading-reference rule could not
    be reached here at all: the foreign slug was stripped and its number returned
    as one of our issues.
    """
    if not text:
        return []
    s = str(text)
    first = _REF_RE.search(s)
    if not first:
        return []
    if _is_foreign_ref(s, first.start()):
        return []
    cluster = _CLUSTER_RE.match(s[first.start():])
    return issue_ref_tokens(cluster.group(0) if cluster else first.group(0))

def _targets_of(raw, what):
    """A claim row's targets: the structured field when present, else the prose.

    Rows written since #329 carry ``issues`` — a list of ints the writer
    recorded at stamp time, so the target is a FACT rather than an inference.
    Rows written before that field fall back to :func:`primary_issue_tokens`.
    """
    structured = raw.get("issues")
    if isinstance(structured, (list, tuple)):
        out = []
        for value in structured:
            try:
                num = int(value)
            except (TypeError, ValueError):
                continue
            if num not in out:
                out.append(num)
        if out:
            return out
    return primary_issue_tokens(what)


def actor_key(by):
    """Collapse a free-text ledger actor into a comparable key.

    Returns ``('uuid', <hex>)`` when any identity token is present, else
    ``('label', <slug>)``. Short 8-hex forms are kept short and compared by
    prefix in :func:`actor_match`, so no roster lookup is needed here.
    """
    s = str(by or "").strip()
    match = _FULL_UUID_RE.search(s)
    if match:
        return ("uuid", match.group(1).lower())
    shorts = _SHORT_UUID_RE.findall(s)
    if shorts:
        return ("uuid", shorts[-1].lower())  # last token: '<role> <uuid>'
    return ("label", _ROLE_PREFIX_RE.sub("", s).strip().lower())


def actor_match(a, b):
    """True when two ledger actor strings denote the SAME lane.

    uuid-vs-uuid compares by prefix (an 8-hex short form is a prefix of the
    full uuid); label-vs-label compares by exact slug. A uuid NEVER matches a
    label: `editor-14` and a bare 8-hex token are different lanes, and guessing
    between them is exactly what let a foreign lane close another lane's claim.
    """
    ka, kb = actor_key(a), actor_key(b)
    if ka[0] == "uuid" and kb[0] == "uuid":
        return ka[1] == kb[1] or ka[1].startswith(kb[1]) or kb[1].startswith(ka[1])
    if ka[0] == "label" and kb[0] == "label":
        return ka[1] != "" and ka[1] == kb[1]
    return False


def is_unattributed(by):
    """True for the 'no resolvable actor' sentinels written by derive_by."""
    s = str(by or "")
    return any(s.startswith(p) for p in UNATTRIBUTED_PREFIXES)


def is_addressed(what, iss):
    """True when ``what`` is ADDRESSED to issue ``iss`` (begins `#N`).

    Tolerates the `STANDDOWN ` keyword: `STANDDOWN #269 (52058a75) — ...`.
    Anchored at the start on purpose — a mere mention mid-sentence is not an
    address (#305).

    #690 (2026-09-28, toolsmith; reported by Triage 530c29ec): the corpus also
    carries a LEADING LEAD-IN form -- `issue #29 close-out: ...`, `Issue #24
    ... LANDED` -- which is just as much an address as the bare form, but the
    start anchor could not read it, so a real done row could not close its own
    claim. Measured live: 42 rows take that form (811 take the bare one), and
    one of them was this lane's own `issue #675 landed a0931587`.
    The arm stays BOUNDED: the address must still BEGIN the row (optionally
    after STANDDOWN/issue), so a mid-sentence mention still closes nothing and
    the #305 fence is unchanged.
    """
    return bool(re.match(r"^\s*(?:STANDDOWN\s+)?(?:issue\s+)?#%d\b" % int(iss),
                         str(what or "").strip(), re.I))


def parse_events(events):
    """Normalise raw ledger events for the predicate.

    Each row gains ``by``/``kind``/``what`` as strings, ``tok`` as a LIST OF
    INTS — one type, so no consumer can compare across types by accident — and
    ``targets``, the issue(s) the row CLAIMS (structured ``issues`` field when
    present, else the leading reference cluster; see #329).
    """
    rows = []
    for idx, e in enumerate(events or []):
        what = e.get("what")
        if what is None:
            what = e.get("text", e.get("summary", e.get("note")))
        what = str(what or "")
        rows.append({
            "idx": idx,
            "n": e.get("n"),
            "by": str(e.get("by") or e.get("actor") or e.get("role") or ""),
            "kind": str(e.get("kind") or e.get("type") or ""),
            "t": str(e.get("t") or e.get("ts") or ""),
            "what": what,
            "tok": issue_ref_tokens(what),
            "targets": _targets_of(e, what),
        })
    return rows


def claim_is_closed(rows, idx, actor, iss):
    """Has the claim at ``rows[idx]`` been closed for issue ``iss``?

    ``rows`` is :func:`parse_events` output; ``iss`` is an int. Implements the
    canonical rule in the module docstring (signals 1-3).
    """
    unattributed = is_unattributed(actor)
    for later in rows[idx + 1:]:
        if later["kind"] not in CLOSING_KINDS:
            continue
        if unattributed or actor_match(actor, later["by"]):
            if iss in later["tok"]:
                return True
        if is_addressed(later["what"], iss):
            return True
    return False


def _open_rows(events, kind, target_issue=None):
    """Shared engine for :func:`open_claims` and :func:`open_holds` (#312).

    ONE loop, so the closure semantics cannot drift between a claim and a hold:
    both are reservations, both are released by the SAME predicate
    (:func:`claim_is_closed` — a later CLOSING_KINDS row for the issue).

    ``target_issue`` restricts the scan to one issue number (int or str). A row
    whose ``what`` carries no issue reference is skipped: every consumer keys on
    the reference, so such a row is a dead letter (and is refused at write time
    since the #19 / dead-letter residual).

    The row's targets are :func:`primary_issue_tokens` (or its structured
    ``issues`` field) — NOT every reference in the note. A row that merely
    MENTIONS another issue in prose does not reserve it (#329), which is what
    produced 13 phantom open claims and a false dispatch refusal.
    """
    rows = parse_events(events)
    target = int(target_issue) if target_issue is not None else None
    out = []
    for idx, row in enumerate(rows):
        if row["kind"] != kind or not row["targets"]:
            continue
        if target is not None and target not in row["targets"]:
            continue
        check = [target] if target is not None else sorted(row["targets"])
        unclosed = [t for t in check if not claim_is_closed(rows, idx, row["by"], t)]
        if unclosed:
            out.append({
                "idx": idx,
                "n": row["n"],
                "by": row["by"],
                "t": row["t"],
                "what": row["what"],
                "tokens": unclosed,
            })
    return out

def open_claims(events, target_issue=None):
    """Every still-OPEN claim row, as dicts (``idx``/``n``/``by``/``t``/``what``/``tokens``).

    A CLAIM is a lane's assertion that it is IMPLEMENTING the issue. For the
    other reservation — a lane that FILED an issue and parked it without
    implementing it — see :func:`open_holds`.
    """
    return _open_rows(events, "claim", target_issue)

def open_holds(events, target_issue=None):
    """Every still-OPEN hold row (kind ``hold``), the same shape as :func:`open_claims`.

    A HOLD is a reservation that is NOT a claim: a lane that FILED an issue and
    parked it (owner design gate, idea box) is not implementing it, so it holds
    no claim row — correctly — and before #312 the dispatcher could not see the
    reservation at all. It re-dispatched an issue its filer still held (#286:
    dispatched twice ~3.5 h apart, then claimed by the SECOND target).

    Stamp one with ``oc-ledger stamp hold "<what>" --by "<lane>"`` (the kind is
    in oc-ledger's v1.3 vocabulary). Release is the claim predicate's: a later
    CLOSING_KINDS row for the issue — ``unclaim`` / ``close`` / ``done`` /
    ``confirm`` / ``reject`` — closes it. A later plain ``claim`` does NOT
    release it, which is harmless: the claim itself already reserves the issue.
    """
    return _open_rows(events, "hold", target_issue)

# ---------------------------------------------------------------------------
# CLAIM FOOTPRINT (#307) — which FILES an issue's work touches
# ---------------------------------------------------------------------------

#: The set of repos that OWN the issue space. An `Issue-Ref` naming a repository
#: OUTSIDE the set is foreign and must never fence an issue here. Measured live
#: 2026-09-18, six commits carried `Issue-Ref: adolfousier/opencrabs#1419` and
#: were skipped as upstream; since v0.4.284 that slug IS the binary tracker, so
#: those six now anchor (correctly) on binary issue 1419.
# HOME_REPO_SLUGS now lives above, with _REF_RE — the prose path shares it (#379).

# `#N` or `<owner>/<repo>#N` — the two forms oc-commit writes.
_SLUG_REF_RE = re.compile(r"^([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)?#(\d+)$")
# A bare integer. Observed live (`295`, `238`, `169`, ...): hand-written values
# that dropped the `#`. Still a fork issue number.
_BARE_REF_RE = re.compile(r"^(\d+)$")

_REC_SEP = "\x1e"
_FLD_SEP = "\x1f"
# git's own ESCAPE syntax for the same bytes. A raw control character in
# `--format=` is rejected (`fatal: invalid --pretty format`), so the command
# line carries `%x1e`/`%x1f` while the PARSER splits on the real bytes git
# then emits.
_REC_ESC = "%x1e"
_FLD_ESC = "%x1f"

def _git(repo_path, *args):
    """Run git in ``repo_path``; return stdout, or None on any failure."""
    if not repo_path or not os.path.isdir(str(repo_path)):
        return None
    try:
        proc = subprocess.run(["git", "-C", str(repo_path)] + list(args),
                              capture_output=True, text=True)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout

def parse_issue_ref_value(value, home_slugs=HOME_REPO_SLUGS, require_slug=False):
    """Issue numbers a single `Issue-Ref` trailer value anchors to.

    HOME space ONLY (v0.4.284): a value naming a repository OUTSIDE
    :data:`HOME_REPO_SLUGS` is foreign and is skipped, so a third-party
    reference cannot fence one of our issues. A value naming any of our three
    trackers (binary `adolfousier/opencrabs`, factory
    `leshchenko1979/opencrabs-dev-factory`, fork `leshchenko1979/opencrabs`)
    anchors normally. One value may carry several references separated by commas
    (`#89,#92,#93`) — every one is returned.

    ``home_slugs`` is the ownership set; a bare string is accepted for
    back-compat and treated as a one-element set.

    ``require_slug`` (default False) REJECTS the bare `#N` form and accepts only
    a slug-qualified value. That is the UPSTREAM-side mode (#356): scanning
    upstream, a bare `#N` trailer names an UPSTREAM issue/PR — a different number
    space from the fork's — so it must not anchor a fork issue. Callers reading
    fork refs leave it False; the upstream reader passes True with
    ``home_slugs=(FORK_SLUG,)``.
    """
    if isinstance(home_slugs, str):
        home_slugs = (home_slugs,)
    out = []
    for part in str(value or "").split(","):
        part = part.strip()
        if not part:
            continue
        match = _SLUG_REF_RE.match(part)
        if match:
            slug, num = match.group(1), int(match.group(2))
            if require_slug and not slug:
                continue
            if slug and slug not in home_slugs:
                continue
            out.append(num)
            continue
        match = _BARE_REF_RE.match(part)
        if match:
            if require_slug:
                continue
            out.append(int(match.group(1)))
    return out

def commit_issue_refs(trailer_value, subject=""):
    """Issue numbers a COMMIT anchors to: the trailer first, subject as fallback.

    The `Issue-Ref` trailer is the anchored citation and wins outright; the
    subject is consulted only when the trailer yields nothing, and then only for
    an EXPLICIT `#<n>` — an unanchored digit run in a subject is not a citation
    (#323: a swap-marker's 8-hex fragment and a `20260917` date stamp both read
    as issue numbers under a bare digit search).

    Returns a LIST, never a scalar: one trailer value may carry several refs
    (`#89,#92,#93`), so a caller matching a target issue must test MEMBERSHIP
    rather than compare against a single parse.

    Why this lives here and not in each caller (#369): the naive
    `re.search(r'#?(\\d+)', value)` this replaces makes the `#` OPTIONAL, so the
    FIRST digit run anywhere in the value wins. A slug-form trailer — the form
    every lane writes — then reads as `1979` from the owner handle in
    `leshchenko1979/opencrabs#341`, and the real issue number is never seen.
    Measured over `git log --all` in the fork (2026-09-19): 9024 commits, 1583
    carrying a non-empty Issue-Ref, of which 181 parse as 1979 and 191 disagree
    with the canonical parse. The counts drift as commits land; the PREDICATE is
    the reproducible part — old = `re.search(r'#?(\\d+)', trailer).group(1)`,
    new = `commit_issue_refs(trailer, subject)[0]`, compared over every commit
    carrying an Issue-Ref. Also refuses a reference naming a repository we do
    NOT own (`acme/widgets#901` yields no issue of ours), which the old form read
    as issue 901.
    """
    refs = parse_issue_ref_value(trailer_value)
    if refs:
        return refs
    match = re.search(r"#(\d+)", str(subject or ""))
    return [int(match.group(1))] if match else []

def issue_ref_index(repo_path, ref="--all", home_slugs=HOME_REPO_SLUGS, require_slug=False):
    """``{sha: [issue, ...]}`` for commits carrying a HOME-space `Issue-Ref`.

    ONE `git log` pass, so a caller resolving many issues pays for it once and
    passes the result on as ``index``. ``ref`` defaults to ``--all`` on
    purpose: a lane's work lives on its own branch until the ff-merge, so a
    fork-main-only scan cannot see it (#307 — issue #262's own lane commits
    were invisible, and its file set came out 3 instead of 5).

    ``home_slugs`` / ``require_slug`` are threaded to
    :func:`parse_issue_ref_value`; the upstream-side reader (#356) passes a
    single fork slug with ``require_slug=True`` so a bare upstream `#N` never
    anchors a fork issue.
    """
    out = _git(repo_path, "log", ref,
               "--format=%H" + _FLD_ESC +
               "%(trailers:key=Issue-Ref,valueonly)" + _REC_ESC)
    index = {}
    if not out:
        return index
    for record in out.split(_REC_SEP):
        record = record.strip("\n")
        if not record:
            continue
        sha, sep, values = record.partition(_FLD_SEP)
        sha = sha.strip()
        if not sha or not sep:
            continue
        nums = []
        # A multi-value trailer field arrives newline-separated.
        for line in values.splitlines():
            for num in parse_issue_ref_value(line, home_slugs=home_slugs,
                                             require_slug=require_slug):
                if num not in nums:
                    nums.append(num)
        if nums:
            index[sha] = nums
    return index

def resolve_issue_commits(repo_path, iss, ref="--all", index=None):
    """Full SHAs of commits that ANCHOR to issue ``iss``.

    Anchored means the commit's `Issue-Ref` trailer names ``iss`` — the
    machine-written link `oc-commit` derives from the actor's ledger claim.
    Prose is never consulted: a commit that merely MENTIONS `#N` in its subject
    or body is not work on `#N`. That was the #307 defect — the old unanchored
    `git log --grep=#N` read upstream commit `1e34378050` (subject `(#478)`,
    body prose `(#300)`) as fork work on #300 and fenced #291's harvest on
    files #291 never touched.

    Returns ``[]`` when nothing anchors — an EMPTY set, never a guess.
    """
    target = int(iss)
    idx = issue_ref_index(repo_path, ref) if index is None else index
    return [sha for sha, nums in idx.items() if target in nums]

#: fork_refs_in_ref memo -- one inverted scan per (repo, ref) per process.
_FORK_REF_INDEX_CACHE = {}

def fork_refs_in_ref(repo_path, ref):
    """``{fork_issue_num: [sha, ...]}`` anchored by an UPSTREAM ref (#356).

    The upstream-side reader. Scanning ``base_ref`` (upstream `adolfousier/main`)
    for a FORK issue cannot use the bare `#N` trailer form: upstream carries bare
    trailers that name UPSTREAM issues, a different number space from the fork's,
    so a bare value must never anchor a fork issue. Only a SLUG-QUALIFIED
    ``leshchenko1979/opencrabs#N`` value counts — hence
    ``home_slugs=(FORK_SLUG,)`` with ``require_slug=True``.

    This replaces an unanchored ``git log --grep='#N'`` over ``base_ref`` whose
    prose match made an unharvested fork issue read as harvested and CLEARED the
    parent/blocker gates (a gate failing OPEN — the third locus of the #307
    class). Cached per (repo, ref): the scan is a full log and a dispatch asks it
    once per parent/blocker/introduced-by issue.
    """
    key = (os.path.abspath(str(repo_path)), str(ref))
    if key not in _FORK_REF_INDEX_CACHE:
        raw = issue_ref_index(repo_path, ref=ref, home_slugs=(FORK_SLUG,),
                              require_slug=True)
        inv = {}
        for sha, nums in raw.items():
            for num in nums:
                inv.setdefault(num, []).append(sha)
        _FORK_REF_INDEX_CACHE[key] = inv
    return _FORK_REF_INDEX_CACHE[key]

def commit_files(repo_path, shas):
    """Union of the paths ``shas`` touch, as a sorted list."""
    files = set()
    shas = [s for s in (shas or []) if s]
    for start in range(0, len(shas), 200):
        chunk = shas[start:start + 200]
        out = _git(repo_path, "log", "--no-walk=unsorted", "--name-only",
                   "--format=" + _REC_ESC, *chunk)
        if not out:
            continue
        for record in out.split(_REC_SEP):
            for line in record.splitlines():
                line = line.strip()
                if line:
                    files.add(line)
    return sorted(files)
def order_commits_parents_first(repo_path, shas):
    """Order commits parents-first; timestamps break ties among ready commits."""
    unique = list(dict.fromkeys(s for s in (shas or []) if s))
    if len(unique) < 2:
        return unique
    wanted = set(unique)
    parents, timestamps = {}, {}
    for sha in unique:
        parts = _git(repo_path, 'show', '-s', '--format=%ct %P', sha).strip().split()
        timestamps[sha] = int(parts[0]) if parts and parts[0].isdigit() else 0
        parents[sha] = set(parts[1:]) & wanted
    ordered, remaining = [], set(unique)
    while remaining:
        ready = [sha for sha in remaining if not (parents.get(sha, set()) & remaining)]
        if not ready:
            ready = list(remaining)
        sha = sorted(ready, key=lambda item: (timestamps.get(item, 0), item))[0]
        ordered.append(sha)
        remaining.remove(sha)
    return ordered


def resolve_issue_files(repo_path, iss, ref="--all", index=None):
    """Files touched by the commits anchoring to issue ``iss``.

    The footprint half of the in-flight fence. An empty list is a legitimate
    answer (nothing anchored) and callers must read it as "no evidence of
    overlap", never as "no other lane is working".
    """
    return commit_files(repo_path, resolve_issue_commits(
        repo_path, iss, ref=ref, index=index))


# ---------------------------------------------------------------------------
# ACTIVE CLAIMS (busy set) -- the still-open claims a scheduler must respect
# ---------------------------------------------------------------------------

# Memoized issue_ref_index -- ONE `git log --all` pass per repo per process.
# get_active_claims resolves a footprint for every open claim and is called
# several times per invocation (busy-set, lane selection, dispatch), and each
# of those resolutions needs the SAME index. Without the memo every call
# re-walks the log. Keyed on the abspath so two spellings of one repo share it.
_ISSUE_REF_INDEX_CACHE = {}


def cached_issue_ref_index(repo_path):
    """issue_ref_index(repo_path), computed once per repo per process."""
    key = os.path.abspath(str(repo_path))
    if key not in _ISSUE_REF_INDEX_CACHE:
        _ISSUE_REF_INDEX_CACHE[key] = issue_ref_index(repo_path)
    return _ISSUE_REF_INDEX_CACHE[key]


def resolve_actor_uuid(by, roster):
    """Best-effort FULL uuid for a claim author, for busy-set comparison.

    A short form is expanded against the roster so that 'editor-1a63f103' and
    'editor 1a63f103-b899-...' collapse to ONE lane and a busy lane is not
    reported idle (#276 -- the stateless avail[0] pinning every unit to a single
    editor happened precisely because the two spellings did not compare equal).
    """
    s = str(by or "")
    match = _FULL_UUID_RE.search(s)
    if match:
        return match.group(1).lower()
    shorts = _SHORT_UUID_RE.findall(s)
    if shorts:
        short = shorts[-1].lower()
        for w in roster:
            if w.startswith(short):
                return w
        return short
    return s.replace("editor ", "").strip()


def get_active_claims(ledger_file, repo_path=None):
    """Every still-OPEN claim as one row per (lane, issue), with its footprint.

    The busy set a scheduler must respect. A missing or malformed ledger
    returns [] DELIBERATELY: the caller-facing contract of the dispatch and
    census in-flight fencing gates is that an unreadable ledger must not refuse
    work. An empty answer means no lane holds an open claim -- never "the ledger
    could not be read", which is why the failure path is silent here and loud
    at the import boundary instead.

    Emitted keys are exactly {'uuid', 'issue', 'what', 'files'} -- the dispatch
    selftest greps them out of this JSON (#305).
    """
    if not os.path.exists(ledger_file):
        return []
    try:
        with open(ledger_file) as f:
            data = json.load(f)
    except Exception:
        return []
    events = data.get("events", [])
    roster = [str(w.get("uuid", "")).lower() for w in data.get("workers", [])]
    rows = parse_events(events)
    claims = []
    for idx, row in enumerate(rows):
        if row["kind"] != "claim" or not row["targets"]:
            continue
        by = row["by"]
        # An AUTHOR-LESS claim row (legacy artifacts carry by:null) names no
        # lane: it can never occupy a lane in the busy set, and under the
        # author-qualified predicate no signal could ever close it, so it would
        # sit in the active list forever. Skip it rather than report a phantom
        # claim owned by the empty uuid.
        if not by.strip():
            continue
        uuid = resolve_actor_uuid(by, roster)
        # One row per TARGET: claim_is_closed answers 'is THIS claim closed for
        # THIS issue', so a multi-issue claim contributes each still-open
        # target. A lane's later row about a DIFFERENT issue must NOT close
        # this one (#305/#425).
        for iss in sorted(row["targets"]):
            if claim_is_closed(rows, idx, by, iss):
                continue
            files = []
            raw = events[idx]
            if "files" in raw and isinstance(raw["files"], list):
                files = raw["files"]
            elif repo_path and os.path.isdir(repo_path):
                # #307: anchored footprint. This leg used to be an unanchored
                # git-log -n 10 --grep=#N, so a commit that merely MENTIONED
                # the issue in prose contributed its files to the claim and
                # fenced an unrelated harvest. An empty list is a REAL answer
                # (nothing anchored) -- no evidence of overlap, never a gap to
                # refill by grepping commit prose.
                files = resolve_issue_files(repo_path, iss,
                                            index=cached_issue_ref_index(repo_path))
            claims.append({
                "uuid": uuid,
                "issue": iss,
                "what": row["what"],
                "filed_ts": row["t"],
                "files": files,
            })
    return claims


#: The manual-records status vocabulary (#564). A unit recorded here was settled
#: BY HAND because the automated upstream check could not settle it.
#:
#: The field exists because the registry had NO way to say "not upstreamable":
#: the lane that settled #209 on 2026-09-15 had only a `pr` field to work with,
#: so it wrote the upstream ISSUE number 1510 there, and the census emitted
#: "manually recorded as filed in PR #1510" -- asserting the OPPOSITE of the
#: decision ledger n=6231 records ("not upstreamable (upstream PR #1510 already
#: carries add_project_repo_remote)"). Absent status means `filed`, so every
#: pre-existing row keeps the meaning it already had.
MANUAL_STATUS_FILED = "filed"
MANUAL_STATUS_NOT_UPSTREAMABLE = "not-upstreamable"
#: #13 (owner, 2026-10-04): a unit that is NOT portable TODAY but BECOMES portable
#: once a prerequisite lands upstream -- *"the harvest tool should differentiate
#: between not upstreamable and conditionally upstreamable, given other PRs are
#: upstreamed first"*. Without it such a unit must be written `not-upstreamable`,
#: which every reader renders as TERMINAL: a welded-shut unit and one waiting on a
#: prerequisite are indistinguishable, and the register loses the dependency that
#: would let the unit be re-considered when its prerequisite lands. The class is
#: measured, not hypothetical: five throttle units (fork #556/#580/#676/#757/#635)
#: each conflict when cherry-picked onto `adolfousier/main`, and their prerequisite
#: is the fork-only telegram governor surface, which has no upstream PR and no
#: issue -- so no dependent PR can be filed today. A conditional row still REFUSES
#: dispatch (it is not harvestable now); what changes is that it says WHY.
MANUAL_STATUS_CONDITIONALLY_UPSTREAMABLE = "conditionally-upstreamable"


def manual_record_status(record):
    """A manual_records row's status, defaulting to `filed`.

    Absent, empty or unknown -> `filed`: the pre-schema meaning, so this
    addition cannot silently reclassify a row that never carried a status.
    An UNRECOGNISED value lands here too -- the fail-safe direction, since
    `filed` is the arm a human re-checks, never a silent terminal refusal.
    """
    st = str((record or {}).get("status") or "").strip().lower()
    if st == MANUAL_STATUS_NOT_UPSTREAMABLE:
        return MANUAL_STATUS_NOT_UPSTREAMABLE
    if st == MANUAL_STATUS_CONDITIONALLY_UPSTREAMABLE:
        return MANUAL_STATUS_CONDITIONALLY_UPSTREAMABLE
    return MANUAL_STATUS_FILED


def manual_record_matches(record, target, target_iss):
    """Does ONE manual_records row cover this target? (#564)

    The same predicate the census has always used, lifted here so the dispatcher
    applies it too: dispatch had ZERO manual handling, so a unit a prior lane
    settled as not-upstreamable was re-proposed on EVERY wave (live instance
    #209, settled 2026-09-15, re-dispatched 2026-09-24 to a lane that could only
    refuse it).
    """
    if not isinstance(record, dict):
        return False
    r_issues = set()
    if record.get("issue"):
        r_issues.add(record.get("issue"))
    if record.get("issues") and isinstance(record.get("issues"), list):
        for i_item in record.get("issues"):
            r_issues.add(i_item)
    by_issue = target_iss is not None and (target_iss in r_issues)
    by_unit = bool(record.get("unit")) and str(record["unit"]).lower() == str(target).lower()
    return bool(by_issue or by_unit)


def manual_record_claim(record, target):
    """One honest sentence about a matching row (#564), WITHOUT the rc prefix.

    Three arms, and the third exists because the registry cannot be trusted to
    hold a PR number. Four live rows carry a `pr` that names no PR: 1510 is an
    upstream ISSUE, and three rows carry `pr: 0`. The old emission rendered
    those as "filed in PR #1510" and "filed in PR #0" -- statements about the
    world that are simply false. A row whose `pr` is falsy is now reported as
    recording NO PR rather than a fabricated one; a row marked not-upstreamable
    says so.
    """
    unit = (record or {}).get("unit")
    tail = " (unit %s)" % unit if unit else ""
    if manual_record_status(record) == MANUAL_STATUS_NOT_UPSTREAMABLE:
        reason = str((record or {}).get("reason") or "").strip()
        why = "; reason: %s" % reason if reason else ""
        return "Target %s is manually recorded as NOT UPSTREAMABLE%s%s" % (target, tail, why)
    if manual_record_status(record) == MANUAL_STATUS_CONDITIONALLY_UPSTREAMABLE:
        reason = str((record or {}).get("reason") or "").strip()
        why = "; condition: %s" % reason if reason else ""
        return ("Target %s is manually recorded as CONDITIONALLY UPSTREAMABLE%s -- it is not "
                "harvestable TODAY, but becomes portable once the prerequisite named here "
                "lands upstream%s" % (target, tail, why))
    pr = (record or {}).get("pr")
    if pr:
        return "Target %s is manually recorded as filed in PR #%s%s" % (target, pr, tail)
    return ("Target %s is manually recorded with NO PR number recorded%s -- the record is "
            "incomplete, or a not-upstreamable marker stored in the pr field without a status"
            % (target, tail))


# ---------------------------------------------------------------------------
# #416 / #455 -- the IDENTITY leg for a merge/landed INFERENCE.
#
# A trailer, a title's `(#N)`, or a branch name is an ATTRIBUTION, never an
# identity (triage.md §Close identity guard, v0.4.216). Three tools consume that
# class of signal, two of them to REFUSE real work:
#
#   * oc-harvest-census   `check` -- a MERGED inference drawn from the PR list
#   * oc-harvest-dispatch `vet`   -- `check_upstream_pr` MERGED
#   * oc-issue-dispatch   LANDED  -- a trailer on a commit (#455)
#
# and a corrupted attribution there refuses PERMANENTLY, because the evidence is
# a commit that sits on adolfousier/main forever. Measured (#416, PR 1557): a PR
# titled `... (#199)` on head `fix/199-pagination-loop-detection` whose changed
# files are under src/brain/ + src/config/ was read as fork issue 199, whose
# surface is src/a2a/ -- an EMPTY intersection, and the refusal could not expire.
#
# The leg: the cited artifact's changed files must INTERSECT the issue's own
# surface before the inference may refuse. ONE home, so the consumers cannot
# drift -- the lesson this module's own docstring records.
# ---------------------------------------------------------------------------

# A repo-relative path named anywhere in an issue's title+body. Anchored to the
# repo's own top-level trees and to a boundary that is not a path character, so
# a URL tail (`.../issues/441`) or a prose word does not read as a path. A
# surface is a SET of tokens: `src/a2a` covers a file under it, and an exact
# path matches itself.
_ISSUE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:tools|src|skills|docs|tests|scripts)/[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*)")


def issue_surface(issue_or_text):
    """The repo-relative paths an issue NAMES (its own title+body).

    Accepts an issue DICT (``title``/``body``) or raw text. Returns a set of
    path tokens; an issue that names no path returns the EMPTY set, which the
    callers treat as FAIL-OPEN -- the identity leg can only ever REMOVE a
    refusal, never invent one.
    """
    if isinstance(issue_or_text, dict):
        text = "%s\n%s" % (issue_or_text.get("title") or "",
                           issue_or_text.get("body") or "")
    else:
        text = str(issue_or_text or "")
    return set(_ISSUE_PATH_RE.findall(text))


def file_on_surface(path, tokens):
    """Does one changed file fall under one of `tokens`?

    Three arms, because a surface token is written by a human and the path is
    written by git:
      * exact -- `src/a2a/handler/notify.rs` == the token;
      * directory prefix -- the token `src/a2a` covers a file under it;
      * basename -- reorg-robust: an issue naming `tools/oc-ledger` still
        matches the file's current home `tools/state/oc-ledger`.
    """
    if not path or not tokens:
        return False
    p = str(path).strip()
    if not p:
        return False
    for t in tokens:
        if not t:
            continue
        if p == t or p.startswith(t + "/"):
            return True
        if p.rsplit("/", 1)[-1] == t.rsplit("/", 1)[-1]:
            return True
    return False


def files_hit_surface(files, tokens):
    """True if ANY changed file falls on the surface.

    `files` may hold plain path strings or `gh pr list --json files` dicts
    (``{"path": ...}``); both are accepted so the caller need not normalise.
    """
    if not files or not tokens:
        return False
    for f in files:
        path = f.get("path") if isinstance(f, dict) else f
        if file_on_surface(path, tokens):
            return True
    return False


def identity_leg_passes(files, tokens):
    """Tri-state identity verdict for a merge/landed inference.

    True when the cited artifact's files INTERSECT the surface; False when both
    sides are known and the intersection is EMPTY (the attribution is corrupt);
    None when the question cannot be answered (no files, or no surface). Callers
    KEEP the refusal on None -- absence of evidence must never turn a refusal
    into an approval.
    """
    if not files or not tokens:
        return None
    return files_hit_surface(files, tokens)


# ---------------------------------------------------------------------------
# #301: a squash-landed upstream PR reads CLOSED, not MERGED
# ---------------------------------------------------------------------------
# GitHub records `mergedAt` only when the merge went through the web UI's merge
# button. A maintainer who applies the work BY HAND -- squash, rebase, or a
# plain cherry-pick -- leaves the PR CLOSED with mergedAt null, and the harvest
# tooling read that as "rejected" and offered the unit for rework. The work was
# already upstream; the rework IS the duplicate PR.
#
# THREE arms, because no single one sees every landing (measured on
# adolfousier/main, 2026-10-06, 4991 commits): the SUBJECT arm alone reads 932
# PRs, the BODY arm alone 62, and their union 987 -- 55 landings are
# BODY-ONLY, invisible to the subject shape because the subject names the
# ISSUE, not the PR. PR #1556 -> issue #133 is exactly that shape:
#   subject: feat(telegram): dedup group history ... (#133)
#   body:    Squashed from PR #1556.
# It is also the #288 case (CLOSED 2026-09-17T14:33:29Z), and a subject-only
# arm re-opened that hole: `census check 133` went back to ELIGIBLE rc=0 --
# the false allow that would file a duplicate upstream PR. Restoring the body
# arm costs 0.42 s vs 0.44 s for the full pass (4.0 MB vs 778 KB), i.e. free.
#
# TWO consumers, one predicate each, no overlap:
#   * the SIGNATURE arms (`squash_signature`) -- the census uses them to
#     PROMOTE a CLOSED PR to MERGED before any verdict; the dispatcher uses them
#     to read a hand-applied landing as already-harvested.
#   * the ANCESTRY arm (`classify_closed_pr_landing`) -- the census's residual
#     verdict for a CLOSED PR the signature did not account for.

_SQUASH_SUBJECT_RE = re.compile(r'\(#(\d{1,6})(?:\s[^)]*)?\)\s*$')
_MERGE_TITLE_RE = re.compile(r'^Merge PR #(\d{1,6})\b')
_BODY_SQUASH_RE = re.compile(r'(?:Squashed from PR|Closes)\s+#(\d+)', re.IGNORECASE)


def squash_signature(records):
    """{pr_number: sha} from a `git log` pass formatted
    `%H%x1f%s%x1f%P%x1f%b%x1e` (sha, subject, parents, body; records split on
    \\x1e because a body is MULTI-LINE). `records` is therefore the stdout split
    on \\x1e, NOT on newlines. Fields after the body are ignored.

    THREE arms, tried in that order, first hit per PR number wins:
      * SUBJECT -- a SQUASH is a SINGLE-PARENT commit whose subject ends `(#N)`,
        the number GitHub appends to a squashed subject;
      * MERGE   -- a merge-button landing has the subject `Merge PR #N`;
      * BODY    -- `Squashed from PR #N` / `Closes #N`. This arm is what finds a
        landing whose subject names the ISSUE and whose PR number exists ONLY in
        the body (#288: PR #1556 -> issue #133), and it costs 0.42 s vs 0.44 s.
    The two SUBJECT arms are restricted to a single-parent commit: on a merge
    commit `(#N)` names the PR of the merge itself and says nothing about what
    it carries, so the arm would mint a false attribution (#416). The BODY arm
    is NOT parent-restricted -- it is the pre-#301 behaviour, restored verbatim,
    and narrowing it is a separate change with its own evidence needs.
    """
    out = {}
    for rec in records:
        if not rec.strip():
            continue
        parts = rec.split('\x1f')
        if len(parts) < 3:
            continue
        sha, subj, parents = parts[0].strip(), parts[1], parts[2].split()
        if not sha:
            continue
        m = None
        if len(parents) == 1:
            m = _SQUASH_SUBJECT_RE.search(subj) or _MERGE_TITLE_RE.match(subj)
        if m:
            out.setdefault(int(m.group(1)), sha)
        body = parts[3] if len(parts) > 3 else ''
        for bm in _BODY_SQUASH_RE.finditer(body):
            out.setdefault(int(bm.group(1)), sha)
    return out


def classify_closed_pr_landing(commits_readable, ancestor_hit):
    """Tri-state landing verdict for a CLOSED upstream PR whose SIGNATURE was
    NOT found upstream. The signature route is `squash_signature` and it is
    consumed SEPARATELY: a CLOSED PR whose number that function yields is
    promoted to MERGED by the census before any verdict is taken, so such a PR
    never reaches this predicate (selftest leg 12 is its control).

    'present' -- the PR's own head commit is an ANCESTOR of the upstream ref,
                 so its work is upstream: the caller must REFUSE the rework.
    'absent'  -- the head commit was readable and is NOT an ancestor, so the
                 work is genuinely not there and rework is legitimate.
    None      -- UNCLASSIFIABLE: the head commit could not be read, so nothing
                 settles it. Absence of evidence must never become an approval
                 (#416), so the caller REFUSES with a NAMED REMEDY rather than
                 defaulting to the allow -- which is exactly the #301 defect:
                 an unclassifiable CLOSED PR fell through to ELIGIBLE_REWORK.
    """
    if ancestor_hit:
        return 'present'
    if not commits_readable:
        return None
    return 'absent'
