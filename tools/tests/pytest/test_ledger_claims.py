"""Ported: ``oc-ledger`` selftest §"claims" — claim refs, closure, the sweep.

Source: ``tools/state/oc-ledger:4105-4767`` (selftest lines 1335-1997) — 95 of
the 475 ``chk`` calls, plus the ``ok``/``bad`` legs that sit between them and
carry the discrimination the ``chk`` arms alone do not. Every assertion message
carries the shell name it replaces in square brackets, so the mapping is
mechanical rather than a claim.

WHAT THIS MODULE PROTECTS
    A claim is the fleet's one durable statement that "this lane is working
    issue #N". Six consumers read it — ``claims``, ``claim-ref``, ``confirm``,
    ``oc-commit``'s Issue-Ref, ``oc-issue-dispatch``, ``sweep-closed-claims`` —
    and each one fails in a DIFFERENT direction when the row it reads is wrong.
    So the invariants here are about which row is read and which row is written:

    * The ADDRESS is the claim, the prose is context. ``claims 76`` must not
      answer for a claim on ``#760``, and a claim written
      ``issue=4242 task='...'`` must not read as CLEAN. ``claim-ref`` derives
      from the FIRST-WRITTEN reference, never from the first ``#<digits>``
      anywhere in the sentence: row n=1585 ("issue 94 ... the #93 options
      hook") derived 93, the wrong issue, which ``confirm`` would then verify
      against GitHub and close.
    * A claim with NO ref is a DEAD LETTER — invisible to ``claims``, so the
      verify-unclaimed gate reports a claimed issue CLEAN. It is refused at
      write time (rc 2) unless ``--allow-no-ref`` says the silence is
      deliberate. A LANDED (``done``/``close``) row with no ref closes nothing
      while reporting "read-back ok": that WARNS, and only for the landing
      kinds, because a ref-less ``confirm`` is a legitimate ship/ACK record.
    * A refusal writes nothing, and an answer that is not an answer is rc 3
      with nothing on stdout. That is why the refusal legs assert the EVENT
      COUNT as well as the rc: a mutant that writes the row and then exits 3
      satisfies an rc-only arm.
    * ``claim-ref``'s ARGUMENT DOMAIN is the uuid. ``claim-ref 4400`` used to
      substring-match a FOREIGN lane's uuid and answer with ITS claim at rc 0 —
      an answer a caller cannot tell from a real one — while ``claim-ref 438``
      matched nothing and read as "no claim". Both are now rc 2, naming the verb
      that DOES take an issue number (``claims <N>``), and the composed
      ``<role> <uuid>`` form that ``derive_by`` EMITS still round-trips.
    * ``--open`` answers the lane's NEWEST claim row that is STILL OPEN, not its
      newest row (#492): closing a newer claim must not make a lane with an
      older open one unresolvable. ``--max-age-d`` (#631) refuses a STALE or
      UNDECIDABLE claim rather than answering, because an Issue-Ref outlives
      the commit that carries it; 0/absent stays unbounded, and a non-numeric
      bound is rc 2 rather than being silently read as 0.
    * Closure vocabulary: ``close``/``done``/``unclaim``/``reject`` are all
      stampable AND all actually close a claim; an UNATTRIBUTED or
      ``unrostered-actor`` claim (no actor to discriminate on) is closable by a
      later closer referencing ``#N``, while an ATTRIBUTED claim is not
      over-closed by a different lane's prose mention.
    * ``sweep-closed-claims`` probes THREE home trackers in BOTH states with
      OPEN WINS: a token open anywhere is never released on the strength of a
      same-numbered closed issue elsewhere. A token on NO tracker is reported
      UNRESOLVED and WITHHOLDS the clean verdict — the false clean printed for
      15 days while n=1678 stayed open against shipped work. ``--dry-run``
      writes nothing; the live sweep writes exactly ONE addressed ``unclaim``
      row per closed issue (deduped across lanes), and one row releases every
      lane's claim on it.
    * The read-back success line is CHARACTER-clipped: ``cut -c1-80`` counted
      bytes under C.UTF-8 and printed a dangling lead byte on the one line whose
      purpose is to let an operator see what landed (#588 sibling).

WHY SOME LEGS CARRY AN ``ok``/``bad`` NAME
    The shell's ``chk`` arms assert an rc; the ``ok``/``bad`` arms beside them
    assert what got WRITTEN or PRINTED. Both are ported, because an rc-only arm
    is satisfied by a verb that refuses everything. Those messages carry the
    ``bad`` name (e.g. ``[sweep-unresolved-false-clean-verdict]``) so the
    mapping covers both halves.

DELIBERATELY NOT PORTED
    No ``chk`` name in the range is dropped and no ``ok``/``bad`` arm is
    dropped; three shapes are FOLDED rather than transcribed:

    * the shell's ``for k in close done unclaim reject`` loop stays one loop, so
      the roster's ``closure-kind-$k-*`` names appear EXPANDED in the messages
      (``[closure-kind-close-claim-rc]``, …) — four instances each, which is
      what ``$k`` means;
    * ``confirm-gh-fail-rc3`` shares its fixture with the ``confirm-ok`` leg
      rather than re-enrolling W2, and
    * every arm that read a temp file the previous line had just written
      (``$T/anon.err``, ``$T/a631.err``, ``$T/sweep.out``, …) reads the
      ``Result`` that produced it, since ``Result`` carries both streams.

FIXTURE NOTE
    The shell drives one shared ``$T`` through a long sequence, so state carries
    forward between legs. Here each leg reaches its precondition by CALLING the
    verb, and the hand-built ledgers the shell writes with ``jq -n`` (sentinel
    actors, an unparseable stamp, two lanes on one issue) come from the
    ``raw_ledger`` factory. That is what lets these run under ``-n 2``, and it
    means a leg cannot pass on state it did not build.

NOTHING HERE IS ``slow``
    No leg drives ``--selftest`` and none sleeps a wall-clock bound: the age
    legs manufacture "stale" with a 2020 stamp and "fresh" with ``now``, and
    every GitHub probe is a stub on ``PATH``. Each leg is a handful of tool
    invocations against a throwaway ledger in this worker's scratch.
"""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")
_SEQ = itertools.count()

# The fixture actors, spelled exactly as the shell's ``local`` block does. W2 is
# the lane ``confirm`` is exercised on; W3 is the ref-less claimant; W4 closes
# #777 and stamps the lesson/shipchain rows; W5 the closure-vocabulary lane; W6
# the no-hash claimant; W7 the "issue N" claimant; W8 the ``--issue`` claimant;
# WC and WO the ``--open`` lanes; W9 the #329 phantom-claim lane; WA/WB/WD the
# ``--max-age-d`` trio (stale / fresh / undateable).
W2 = "11111111-2222-3333-4444-555555555555"
W3 = "22222222-3333-4444-5555-666666666666"
W4 = "44444444-3333-4444-5555-666666666666"
W5 = "55555555-3333-4444-5555-666666666666"
W6 = "66666666-3333-4444-5555-666666666666"
W7 = "77777777-3333-4444-5555-666666666666"
W8 = "88888888-3333-4444-5555-666666666666"
W9 = "editor 99999999-9999-9999-9999-999999999999"
WC = "cccccccc-3333-4444-5555-666666666666"
WO = "abcdef01-2345-6789-abcd-ef0123456789"
WF = "44004400-1111-2222-3333-444444444444"   # the FOREIGN lane ('4400' sits in it)
WA = "aaaa6310-1111-4222-8333-444455556666"
WB = "bbbb6310-1111-4222-8333-444455556666"
WD = "dddd6310-1111-4222-8333-444455556666"

# The live ledger's claim-address shapes, verbatim from the rows the shell cites.
CLAIM_NO_HASH = "issue=4242 task='fixture ref without a hash'"
CLAIM_SUBSTRING_TRAP = "CLAIM #760 — fixture substring trap"
CLAIM_MENTION = ("filed fragility class issue (#327): one proven live break "
                 "(#323)")
NO_REF_WARN = "NO parseable issue reference"   # the shell's ``_lw``


# =============================================================================
# helpers — one invocation each, so a leg reads as the verb it drives
# =============================================================================
def _run(run_tool, *args, env=None, timeout=180):
    return run_tool([str(TOOL)] + [str(a) for a in args], timeout=timeout,
                    env=env)

def _as(actor):
    """The env override that makes one invocation act as ``actor``.

    Per-invocation rather than per-test: the shell's legs deliberately interleave
    actors inside one section (W2's confirm, W3's ref-less claim), and the
    ambient ``OC_ACTOR`` must stay the sandbox's own.
    """
    return {"OC_ACTOR": actor}

def _enroll(run_tool, uuid, role="tester", topic=42):
    res = _run(run_tool, "enroll", uuid, role, "--topic", topic)
    assert res.rc == 0, (
        "fixture precondition: enroll %s failed rc=%s\n%s"
        % (uuid, res.rc, res.combined[-600:]))
    return res

def _last_by(ledger, uuid):
    """The lane's last event — the shell's
    ``[.events[] | select((.by // "") | contains($u))][-1]``.

    ``contains``, not equality: a row is attributed as ``<role> <uuid>`` or as
    ``unrostered-actor <uuid>``, and both must resolve to the lane.
    """
    rows = [e for e in L.events(ledger) if uuid in (e.get("by") or "")]
    return rows[-1] if rows else None

@pytest.fixture
def raw_ledger(scratch):
    """Factory: ``raw_ledger(tag, events, workers=())`` -> a hand-built ledger.

    The shell builds several fixtures with ``jq -n`` because the SHAPE is the
    assertion (a row whose ``by`` is the unattributed sentinel, an event whose
    ``t`` is unparseable, two lanes claiming one issue). Those ledgers are not
    reachable through the verbs, so they are written directly — with the two
    keys the tool's own reader expects.
    """
    def _make(tag, events, workers=()):
        d = scratch.path / "raw" / ("%s-%d" % (tag, next(_SEQ)))
        d.mkdir(parents=True, exist_ok=True)
        p = d / "ledger.json"
        p.write_text(json.dumps({"workers": list(workers),
                                 "events": list(events)}), encoding="utf-8")
        return p
    return _make

# =============================================================================
# 1. confirm — the flip, the scanned row, and the three-tracker probe
# =============================================================================
def test_confirm_flips_the_worker_and_appends_the_row_claims_scans(
        ledger_sandbox, run_tool, gh_stub):
    """``confirm-ok`` + ``confirm-flipped`` + ``confirm-event``.

    ``confirm`` is the only verb that may set ``workers[].confirmed``, and the
    D-2 defect was that it wrote ONLY to ``workers[].events`` — a store
    ``cmd_claims`` never reads — so the claim stayed OPEN forever while the verb
    reported success. The assertion therefore reads BOTH stores: the flag AND
    the top-level ``.events`` row that the scanner keys on.
    """
    ledger = Path(ledger_sandbox.ledger)
    _enroll(run_tool, W2)
    res = _run(run_tool, "stamp", "claim", "CLAIM #999 — fixture claim for confirm",
               env=_as(W2))
    assert res.rc == 0, "fixture precondition: claim rc=%s\n%s" % (
        res.rc, res.combined[-600:])

    gh = gh_stub(rules=[("issue view", "{}", 0)])
    res = _run(run_tool, "confirm", W2, "--gh", str(gh))
    assert res.rc == 0, "[confirm-ok] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-800:])

    row = [w for w in L.workers(ledger) if w.get("uuid") == W2]
    assert row and row[0].get("confirmed") is True, (
        "[confirm-flipped] workers[] %s confirmed=%r, want True — confirm is "
        "the only verb allowed to flip it"
        % (W2, row[0].get("confirmed") if row else None))

    assert row[0]["events"][-1]["kind"] == "confirm", (
        "[confirm-event] the worker's last nested event is %r, want 'confirm'"
        % (row[0]["events"][-1].get("kind"),))

    # The DISCRIMINATING half (D-2): the row the scanner reads is top-level.
    scanned = L.where(ledger, kind="confirm")
    assert scanned, (
        "[confirm-event] confirm wrote no TOP-LEVEL .events row — cmd_claims "
        "scans only that store, so the claim would read OPEN forever (D-2, "
        "HQ d72bd52d)")
    assert W2 in (scanned[-1].get("by") or ""), (
        "[confirm-event] the top-level confirm row is attributed %r, want it to "
        "CONTAIN %s — the closure link is a contains() test"
        % (scanned[-1].get("by"), W2))

def test_a_confirm_that_cannot_verify_the_issue_is_refused_and_changes_nothing(
        ledger_sandbox, run_tool, gh_stub):
    """``confirm-gh-fail-rc3`` + ``confirm-probes-factory-tracker-rc0``
    + ``confirm-probes-binary-tracker-rc0`` + ``confirm-no-github-rc3``.

    v0.4.284 widened the probe to ALL THREE home trackers, so the stub answers
    for exactly one of them and fails the others. The pair is a CONTROL: a probe
    that still asked only the fork fails the factory leg, and a ``_found``
    hardwired to 1 fails the fail-all leg. Each refusal must also leave
    ``confirmed`` false and the event count unchanged — an rc-3 that took the
    confirmation anyway is the defect the rc is standing in for.
    """
    ledger = Path(ledger_sandbox.ledger)
    _enroll(run_tool, W2)
    res = _run(run_tool, "stamp", "claim", "CLAIM #999 — fixture claim for confirm",
               env=_as(W2))
    assert res.rc == 0, "fixture precondition: claim rc=%s\n%s" % (
        res.rc, res.combined[-600:])

    def _unconfirm():
        doc = L.read_json(ledger)
        for w in doc["workers"]:
            if w.get("uuid") == W2:
                w["confirmed"] = False
        ledger.write_text(json.dumps(doc, indent=1), encoding="utf-8")

    def _confirm_with(gh):
        _unconfirm()
        before = len(L.events(ledger))
        res = _run(run_tool, "confirm", W2, "--gh", str(gh))
        after = len(L.events(ledger))
        row = [w for w in L.workers(ledger) if w.get("uuid") == W2][0]
        return res, before, after, row

    # (a) the tracker knows nothing about #999 -> refuse.
    fail = gh_stub(rules=[], default_rc=1, name="gh-fail")
    res, before, after, row = _confirm_with(fail)
    assert res.rc == 3, "[confirm-gh-fail-rc3] rc=%s, want 3\n%s" % (
        res.rc, res.combined[-600:])
    assert after == before and row.get("confirmed") is False, (
        "[confirm-gh-fail-rc3] the refused confirm wrote %d row(s) and left "
        "confirmed=%r — a refusal that still takes the confirmation is the "
        "defect the rc is standing in for"
        % (after - before, row.get("confirmed")))

    # (b) only the FACTORY tracker resolves it -> accepted (one of three).
    factory = gh_stub(rules=[("opencrabs-dev-factory", "{}", 0)], default_rc=1,
                      name="gh-factory")
    res, _b, _a, _r = _confirm_with(factory)
    assert res.rc == 0, (
        "[confirm-probes-factory-tracker-rc0] rc=%s, want 0 — the probe must "
        "ask every home tracker, not just the fork\n%s"
        % (res.rc, res.combined[-600:]))

    # (c) only the BINARY (upstream) tracker resolves it -> accepted too.
    binary = gh_stub(rules=[("opencrabs/opencrabs", "{}", 0)], default_rc=1,
                     name="gh-binary")
    res, _b, _a, _r = _confirm_with(binary)
    assert res.rc == 0, (
        "[confirm-probes-binary-tracker-rc0] rc=%s, want 0 — opencrabs/"
        "opencrabs is one OF OURS (v0.4.284)\n%s"
        % (res.rc, res.combined[-600:]))

    # (d) no gh at all -> refuse, never take.
    _unconfirm()
    before = len(L.events(ledger))
    res = _run(run_tool, "confirm", W2,
               env={"GH_BIN": str(Path(ledger_sandbox) / "no-such-gh-binary")})
    assert res.rc == 3, (
        "[confirm-no-github-rc3] rc=%s, want 3 — an unavailable gh must never "
        "be read as 'verified'\n%s" % (res.rc, res.combined[-600:]))
    assert len(L.events(ledger)) == before, (
        "[confirm-no-github-rc3] the refusal appended a row — 'cannot check' "
        "must not become 'checked'")

# =============================================================================
# 2. claim-ref — the derivation and the composed round trip
# =============================================================================
def test_claim_ref_derives_the_issue_and_round_trips_the_composed_form(
        ledger_sandbox, run_tool):
    """``claim-ref-after-claim`` + ``claim-ref-value`` + ``claim-ref-composed-rc0``
    + ``claim-ref-composed-value`` + ``claim-ref-composed-bad-tail-rc2``.

    M2-24 (#441): ``derive_by`` EMITS the composed ``<role> <uuid>`` form, so
    that form must keep resolving — and the same domain guard must still refuse
    a composed value whose TAIL is not a uuid (otherwise "role <anything>" would
    be an accepted actor).
    """
    _enroll(run_tool, W2)
    res = _run(run_tool, "stamp", "claim", "CLAIM #999 — fixture claim for confirm",
               env=_as(W2))
    assert res.rc == 0, "fixture precondition: claim rc=%s\n%s" % (
        res.rc, res.combined[-600:])

    res = _run(run_tool, "claim-ref", W2)
    assert res.rc == 0, "[claim-ref-after-claim] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert res.out.strip() == "999", (
        "[claim-ref-value] stdout=%r, want '999' — the ref must be the bare "
        "number a caller can paste into a trailer" % (res.out,))

    res = _run(run_tool, "claim-ref", "tester %s" % W2)
    assert res.rc == 0, (
        "[claim-ref-composed-rc0] rc=%s, want 0 — the form derive_by emits must "
        "resolve\n%s" % (res.rc, res.combined[-600:]))
    assert res.out.strip() == "999", (
        "[claim-ref-composed-value] stdout=%r, want '999'" % (res.out,))

    res = _run(run_tool, "claim-ref", "tester not-a-uuid")
    assert res.rc == 2, (
        "[claim-ref-composed-bad-tail-rc2] rc=%s, want 2 — a composed form whose "
        "TAIL is not a uuid is a usage error, not a lane\n%s"
        % (res.rc, res.combined[-600:]))

# =============================================================================
# 3. a claim without a ref is refused; the hatch is explicit
# =============================================================================
def test_a_claim_must_carry_a_ref_and_the_hatch_is_the_only_way_past(
        ledger_sandbox, run_tool):
    """``stamp-claim-no-ref-refused`` + ``stamp-claim-foreign-only-refused``
    + ``stamp-claim-binary-tracker-anchors`` + ``stamp-claim-binary-tracker-ref-value``
    + ``stamp-claim-no-ref-hatch-rc`` + ``claim-ref-no-ref-rc3``.

    A ref-less claim is a DEAD LETTER: ``cmd_claims`` cannot see it, so the
    verify-unclaimed gate reports a claimed issue CLEAN. The foreign/binary pair
    is a CONTROL — a predicate that accepted every slug would pass the anchor
    leg vacuously — and both refusals are counted, because rc 2 that still
    wrote the row is the same defect with a nicer exit code.
    """
    ledger = Path(ledger_sandbox.ledger)
    before = len(L.events(ledger))

    res = _run(run_tool, "stamp", "claim", "CLAIM without issue ref", env=_as(W3))
    assert res.rc == 2, (
        "[stamp-claim-no-ref-refused] rc=%s, want 2 — a claim no consumer can "
        "address is refused at write time (symmetric with #19)\n%s"
        % (res.rc, res.combined[-600:]))

    res = _run(run_tool, "stamp", "claim",
               "CLAIM third-party acme/widgets#7 only", env=_as(W3))
    assert res.rc == 2, (
        "[stamp-claim-foreign-only-refused] rc=%s, want 2 — a ref qualified by "
        "a repository we do not own is not a home-space ref (#379)\n%s"
        % (res.rc, res.combined[-600:]))

    assert len(L.events(ledger)) == before, (
        "two refused claims wrote %d row(s) — the dead-letter guard must be a "
        "no-op on the record, not just on the rc"
        % (len(L.events(ledger)) - before))

    res = _run(run_tool, "stamp", "claim",
               "CLAIM upstream opencrabs/opencrabs#1419 only", env=_as(W3))
    assert res.rc == 0, (
        "[stamp-claim-binary-tracker-anchors] rc=%s, want 0 — opencrabs/"
        "opencrabs is the binary tracker and one of OURS\n%s"
        % (res.rc, res.combined[-600:]))

    res = _run(run_tool, "claim-ref", W3)
    assert res.out.strip() == "1419", (
        "[stamp-claim-binary-tracker-ref-value] claim-ref=%r, want '1419' — the "
        "anchor is only real if the derivation sees it" % (res.out,))

    res = _run(run_tool, "stamp", "claim", "CLAIM without issue ref",
               "--allow-no-ref", env=_as(W3))
    assert res.rc == 0, (
        "[stamp-claim-no-ref-hatch-rc] rc=%s, want 0 — --allow-no-ref is the "
        "deliberate override (#19 has --allow-unattributed, sync has "
        "--allow-sweep)\n%s" % (res.rc, res.combined[-600:]))

    res = _run(run_tool, "claim-ref", W3)
    assert res.rc == 3, (
        "[claim-ref-no-ref-rc3] rc=%s, want 3 — the row landed, but it carries "
        "no ref, and that is the honest verdict rather than a silent clean\n%s"
        % (res.rc, res.combined[-600:]))
    assert not res.out.strip(), (
        "[claim-ref-no-ref-rc3] stdout=%r on a refusal — a consumer reading "
        "stdout would take it as a ref" % (res.out,))

# =============================================================================
# 4. a landed row that addresses nothing WARNS; a ship record does not
# =============================================================================
def test_a_ref_less_landing_warns_while_a_ref_less_ship_record_stays_silent(
        ledger_sandbox, run_tool):
    """``stamp-done-ref-less-WARNS`` + ``stamp-done-with-ref-is-silent``
    + ``stamp-confirm-ref-less-is-silent`` + ``stamp-done-no-ref-hatch-silent``
    + ``claim-ref-no-claim-rc3``.

    Measured 2026-09-25: ``stamp done "592 landed: b9ee661cc"`` returned
    "read-back ok" rc 0 and left the claim OPEN — "(read-back ok)" confirms the
    WRITE, never the ADDRESSING. BARE DIGITS ARE NOT A REF. The warn is scoped
    to the LANDED kinds: of 22 ref-less closing rows in the live ledger, 6 are
    ``confirm`` ship/ACK records that legitimately carry no issue, so a blanket
    warn would fire on every legitimate one — which is what makes the silent
    arms controls rather than restatements.
    """
    ledger = Path(ledger_sandbox.ledger)
    before = len(L.events(ledger))

    res = _run(run_tool, "stamp", "done", "601 landed: b9ee661cc", env=_as(W3))
    assert res.combined.count(NO_REF_WARN) == 1, (
        "[stamp-done-ref-less-WARNS] the warn fired %d time(s), want 1 — bare "
        "digits are not a ref, so this row closes NOTHING while reporting "
        "success: %r"
        % (res.combined.count(NO_REF_WARN), res.combined[-600:]))
    assert res.rc == 0, (
        "[stamp-done-ref-less-WARNS] rc=%s, want 0 — a WARN is not a refusal "
        "(a hard gate would break the legitimate ship/ACK pattern)\n%s"
        % (res.rc, res.combined[-600:]))

    res = _run(run_tool, "stamp", "done", "#601 landed: b9ee661cc", env=_as(W3))
    assert NO_REF_WARN not in res.combined, (
        "[stamp-done-with-ref-is-silent] the warn fired on a row that DOES "
        "address #601: %r" % (res.combined[-600:],))

    res = _run(run_tool, "stamp", "confirm",
               "v0.4.124 batch SHIPPED: sync ok", env=_as(W3))
    assert NO_REF_WARN not in res.combined, (
        "[stamp-confirm-ref-less-is-silent] the warn fired on a ref-less "
        "CONFIRM — 6 such rows exist in the live ledger and every one is a "
        "legitimate ship/ACK record: %r" % (res.combined[-600:],))

    res = _run(run_tool, "stamp", "done", "--allow-no-ref",
               "deliberately ref-less", env=_as(W3))
    assert NO_REF_WARN not in res.combined, (
        "[stamp-done-no-ref-hatch-silent] --allow-no-ref still warns: %r"
        % (res.combined[-600:],))

    # The rows above DID land (a warn that also dropped the write would pass
    # every arm above), which is exactly why the next leg must answer rc 3.
    assert len(L.events(ledger)) == before + 4, (
        "the four warn legs wrote %d row(s), want 4 — a WARN must not suppress "
        "the write" % (len(L.events(ledger)) - before))

    res = _run(run_tool, "claim-ref", "00000000-0000-0000-0000-000000000000")
    assert res.rc == 3, (
        "[claim-ref-no-claim-rc3] rc=%s, want 3 — a lane with no claim at all "
        "is rc 3, distinct from 'has claims, none with a ref'\n%s"
        % (res.rc, res.combined[-600:]))


# =============================================================================
# 5. the read-back line is CHARACTER-safe and still clipped (#588 sibling)
# =============================================================================
def test_the_read_back_line_clips_by_characters_and_stays_decodable(
        ledger_sandbox, run_tool):
    """``stamp-read-back-clipped-to-80-chars`` + ``stamp-len-reports-characters-not-bytes``.

    ``cut -c1-80`` counts BYTES under C.UTF-8, so a ``what`` holding non-ASCII
    clipped mid-character and printed a dangling lead byte on the one line whose
    entire purpose is to let an operator see what landed. The fixture is 106
    CHARACTERS (6-byte prefix + 100 three-byte marks = 306 bytes), so the clip
    fires and byte offset 80 lands two bytes INTO the 25th mark — a fixture sized
    by eye can sit under the cap and assert a boundary it never reached.

    Two independent halves, which is why both are asserted: the clip must still
    BOUND (a fix that stopped clipping would pass a decodability-only leg) and
    ``len=`` must count CHARACTERS (106, not 306).
    """
    payload = "#601  " + "\u2705" * 100
    assert len(payload) == 106 and L.byte_len(payload) == 306, (
        "fixture precondition: payload is %d chars / %d bytes, want 106 / 306 — "
        "the clip only discriminates if the two differ"
        % (len(payload), L.byte_len(payload)))

    res = _run(run_tool, "stamp", "done", payload, env=_as(W3))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])

    # A mid-character cut leaves a lone lead byte, which conftest's
    # errors="replace" decode turns into U+FFFD — so its ABSENCE is the
    # decodability assertion, and it fails on exactly the #588 defect.
    assert "\ufffd" not in res.combined, (
        "stamp read-back line is NOT valid UTF-8 with a multi-byte what "
        "(#588): the clip cut mid-character and printed a dangling lead "
        "byte: %r" % (res.combined[-300:],))

    m = re.search(r'what="(.*)" len=(\d+) hash8=([0-9a-f]{8})', res.combined)
    assert m, (
        "the read-back line does not have the shape what=\"…\" len=N hash8=…: "
        "%r" % (res.combined[-300:],))

    assert len(m.group(1)) == 80, (
        "[stamp-read-back-clipped-to-80-chars] the surfaced what is %d "
        "CHARACTERS, want 80 — the fix must not stop clipping"
        % len(m.group(1)))

    assert m.group(2) == "106", (
        "[stamp-len-reports-characters-not-bytes] len=%s, want 106 (306 BYTES) "
        "— a byte count would make len= agree with a wrong payload" % m.group(2))

# =============================================================================
# 6. the ARGUMENT DOMAIN — a bare number is not an actor (#441)
# =============================================================================
def test_the_claim_ref_argument_domain_refuses_numbers_and_fragments(
        ledger_sandbox, run_tool, raw_ledger):
    """``claim-ref-foreign-lane-rc0`` + ``claim-ref-foreign-lane-value``
    + ``claim-ref-non-uuid-rc2`` + ``claim-ref-non-uuid-hint``
    + ``claim-ref-non-uuid-no-stdout`` + ``claim-ref-fragment-rc2``
    + ``claim-ref-short-uuid-rc2`` + ``claim-ref-nonhex-uuid-rc2``
    + ``claims-4242-rc``.

    Until #441 this verb validated PRESENCE only, so ``claim-ref 4400`` — a
    fragment of a FOREIGN lane's uuid — substring-matched that lane and answered
    with ITS claim at rc 0. That is a lie a caller cannot tell from a real
    answer, which is why the foreign lane lives in its own ledger here: the
    fixture proves the ref EXISTS and is reachable by uuid, and the same call
    spelled as a fragment is refused.

    The two arguments fail in OPPOSITE directions pre-fix ('4400' answers at rc
    0, '438' matches nothing and reads as "no claim"), which is why the failure
    MODE was unlearnable from the argument — hence the hint naming the verb that
    does take an issue number.
    """
    dom = raw_ledger("dom", [], workers=[
        {"uuid": WF, "role": "tester", "topic_id": 43, "feature": "-",
         "confirmed": True, "last_acked": None, "notes": [], "events": []}])
    env = {"OC_LEDGER": str(dom)}

    res = _run(run_tool, "stamp", "claim", "CLAIM #4242 — foreign-lane fixture",
               env=dict(env, **_as(WF)))
    assert res.rc == 0, "fixture precondition: rc=%s\n%s" % (
        res.rc, res.combined[-600:])

    res = _run(run_tool, "claim-ref", WF, env=env)
    assert res.rc == 0, (
        "[claim-ref-foreign-lane-rc0] rc=%s, want 0 — the ref is there and the "
        "FULL uuid resolves it\n%s" % (res.rc, res.combined[-600:]))
    assert res.out.strip() == "4242", (
        "[claim-ref-foreign-lane-value] stdout=%r, want '4242'" % (res.out,))

    # THE LIE: the fragment of that uuid, pre-fix answered 4242 at rc 0.
    res = _run(run_tool, "claim-ref", "4400", env=env)
    assert res.rc == 2, (
        "[claim-ref-non-uuid-rc2] rc=%s, want 2 — a bare issue number is not an "
        "actor, and substring-matching a foreign lane is the defect\n%s"
        % (res.rc, res.combined[-600:]))
    assert "claims <N>" in res.err, (
        "[claim-ref-non-uuid-hint] stderr does not name the verb that DOES take "
        "an issue number, so the caller is told 'refused' with no remedy: %r"
        % (res.err[-400:],))
    assert not res.out.strip(), (
        "[claim-ref-non-uuid-no-stdout] stdout=%r on a refusal — a consumer "
        "piping stdout would take the fragment's claim as an answer" % (res.out,))

    # Three near-miss spellings of the SAME uuid, one per way a caller
    # abbreviates it: a 4-char prefix, the body with the first group truncated,
    # and a trailing character that is not hex. Each must be rc 2, because a
    # lenient "looks close enough" match here is the substring defect again with
    # a longer needle.
    res = _run(run_tool, "claim-ref", "2fae")
    assert res.rc == 2, (
        "[claim-ref-fragment-rc2] claim-ref '2fae' rc=%s, want 2 — a 4-char "
        "session prefix is a log handle, not an actor\n%s"
        % (res.rc, res.combined[-600:]))

    res = _run(run_tool, "claim-ref", "4400-1111-2222-3333-444444444444")
    assert res.rc == 2, (
        "[claim-ref-short-uuid-rc2] claim-ref on the 8-char first group + body "
        "rc=%s, want 2 — that is a uuid with a digit missing, and accepting it "
        "would mean normalising away a typo\n%s"
        % (res.rc, res.combined[-600:]))

    res = _run(run_tool, "claim-ref", "44004400-1111-2222-3333-44444444444Z")
    assert res.rc == 2, (
        "[claim-ref-nonhex-uuid-rc2] claim-ref with a trailing 'Z' rc=%s, want "
        "2 — right length and shape but not hex is still not a uuid\n%s"
        % (res.rc, res.combined[-600:]))

    # AC-1, the substantive half: the failure names the verb that DOES take an
    # issue number, and that verb actually answers for it.
    res = _run(run_tool, "claims", "4242", env=env)
    assert res.rc == 0, (
        "[claims-4242-rc] rc=%s, want 0 — the remedy the refusal points at must "
        "work\n%s" % (res.rc, res.combined[-600:]))
    assert WF in res.out and "#4242" in res.out, (
        "[claims-4242-row] claims 4242 printed %r — want the row for %s on "
        "#4242" % (res.out, WF))

def test_a_ref_less_claim_keeps_its_own_diagnostic_not_the_domain_one(
        ledger_sandbox, run_tool):
    """``claim-ref-no-ref-rc3-kept`` + ``claim-ref-no-ref-diagnostic-kept``.

    W3 DOES hold a claim row — it is the REF that is missing, so the diagnostic
    is the SECOND branch of ``_latest_claim_issue``. A domain guard that
    swallowed this case into "not a uuid" would redden here, which is why the
    exact text is pinned rather than the rc alone: both failures are rc 3.
    """
    res = _run(run_tool, "stamp", "claim", "CLAIM without issue ref",
               "--allow-no-ref", env=_as(W3))
    assert res.rc == 0, "fixture precondition: rc=%s\n%s" % (
        res.rc, res.combined[-600:])

    res = _run(run_tool, "claim-ref", W3)
    assert res.rc == 3, (
        "[claim-ref-no-ref-rc3-kept] rc=%s, want 3\n%s"
        % (res.rc, res.combined[-600:]))
    assert ("latest claim by %s carries no numeric issue ref" % W3) in res.err, (
        "[claim-ref-no-ref-diagnostic-kept] stderr is %r, want it to say the "
        "claim EXISTS and lacks a ref — 'not a uuid' would be a different bug "
        "wearing the same rc" % (res.err[-400:],))

# =============================================================================
# 7. the ref the SCANNER reads: first-written token, and --issue wins
# =============================================================================
def test_claim_ref_reads_the_first_written_ref_not_the_first_hash(
        ledger_sandbox, run_tool):
    """``claim-ref-nohash-rc`` + ``claim-ref-nohash-value`` +
    ``claim-issue-flag-wins-rc`` + ``claim-issue-flag-wins-target``
    + ``claim-issue-flag-wins-prose`` + ``claim-issue-hash-normalised``
    + ``claim-issue-leading-cluster-verbatim``.

    Ref extraction is the SINGLE OWNER's (``_issue_ref_tokens``), so (a) a claim
    written ``issue N`` with no '#' resolves at all, and (b) the FIRST-WRITTEN
    ref wins. Fixture shape from live row n=1585 ("issue 94 ... the #93 options
    hook"): the old "first '#<digits>' anywhere" grep derived 93 — the wrong
    issue, which ``confirm`` would then verify against GitHub and close.

    #335: an explicit ``--issue`` must WIN over a prose mention. The old prefix
    check was a SUBSTRING search over the whole prose, so a lane claiming #299
    while narrating "fixed #294" had its prefix suppressed and the row anchored
    on #294 — and ``oc-commit`` derived Issue-Ref #294 from it.
    """
    ledger = Path(ledger_sandbox.ledger)

    res = _run(run_tool, "stamp", "claim",
               "issue 6060 claimed: no hash form; a passing mention of the "
               "#7070 hook", env=_as(W7))
    assert res.rc == 0, "[claim-ref-nohash-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    res = _run(run_tool, "claim-ref", W7)
    assert res.out.strip() == "6060", (
        "[claim-ref-nohash-value] claim-ref=%r, want '6060' — the 'issue N' "
        "form carries no '#' and the old grep answered rc 3 for a claim that "
        "EXISTS" % (res.out,))

    res = _run(run_tool, "claim", "--issue", "299",
               "--what", "fixed #294 (superseded), now claiming #299",
               env=_as(W8))
    assert res.rc == 0, "[claim-issue-flag-wins-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    row = _last_by(ledger, W8)
    assert row.get("issues") == [299], (
        "[claim-issue-flag-wins-target] the row's structured issues=%r, "
        "want [299] — the explicit --issue is the ADDRESS, the #294 mention is "
        "context (#335)" % (row.get("issues"),))
    res = _run(run_tool, "claim-ref", W8)
    assert res.out.strip() == "299", (
        "[claim-issue-flag-wins-prose] claim-ref=%r, want '299' — deriving "
        "#294 would post the commit's comment onto a finished issue"
        % (res.out,))

    # `--issue #N` must normalise: a stray '#' used to build "CLAIM ##N", which
    # both looked wrong AND dodged the membership test.
    res = _run(run_tool, "claim", "--issue", "#298", "--what", "second fixture",
               env=_as(W8))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    row = [e for e in L.events(ledger)
           if W8 in (e.get("by") or "") and "second fixture" in (e.get("what") or "")][0]
    assert row["what"].startswith("CLAIM #298 — ") and "##" not in row["what"], (
        "[claim-issue-hash-normalised] the stored text is %r, want it to "
        "lead 'CLAIM #298 — ' with no '##'" % (row["what"],))

    # ...and a prose that ALREADY leads with the claim cluster is kept verbatim
    # (the suppression is still correct in the one case it was written for).
    res = _run(run_tool, "claim", "--issue", "297",
               "--what", "CLAIM #297 — already led", env=_as(W8))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    row = [e for e in L.events(ledger)
           if W8 in (e.get("by") or "") and "already led" in (e.get("what") or "")][0]
    assert row["what"] == "CLAIM #297 — already led", (
        "[claim-issue-leading-cluster-verbatim] stored %r, want the prose "
        "verbatim — the row already leads with its own cluster"
        % (row["what"],))

# =============================================================================
# 8. `--open` — the ref a consumer may ACT on (#335, #492)
# =============================================================================
def test_claim_ref_open_refuses_a_closed_claim_and_its_own_usage_errors(
        ledger_sandbox, run_tool):
    """``claim-ref-open-closed-rc3`` + ``claim-ref-open-repeat-rc3``
    + ``claim-ref-open-before-uuid-rc3`` + ``claim-ref-unknown-flag-rc2``
    + ``claim-ref-open-no-uuid-rc2`` + ``claim-ref-open-live-rc``
    + ``claim-ref-open-live-value`` + ``claim-ref-open-released-rc3``
    + ``claim-ref-plain-ignores-closure``.

    ``--open`` is the only ref ``oc-commit`` may derive an Issue-Ref from, so
    "closed" must be rc 3 with NOTHING on stdout — while the PLAIN form keeps
    answering, because a diagnostic verb still wants to know what the lane last
    claimed. The two are asserted side by side on the SAME lane: a verb that
    refused both would pass an ``--open``-only leg.
    """
    ledger = Path(ledger_sandbox.ledger)
    _enroll(run_tool, W2)
    res = _run(run_tool, "stamp", "claim", "CLAIM #999 — fixture claim for confirm",
               env=_as(W2))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])

    # W2's #999 is CLOSED by a confirm — the same closing kind the fleet uses.
    res = _run(run_tool, "stamp", "confirm", "CONFIRM #999 — fixture closure",
               env=_as(W2))
    assert res.rc == 0, "precondition: confirm rc=%s\n%s" % (
        res.rc, res.combined[-600:])

    # Three spellings that all reach the SAME closure verdict. NOTE what the
    # shell actually proved here: it asserted rc 3 on a CLOSED lane, so these
    # names are about the closure answer, NOT about argument validation —
    # `--open --open` and `--open` before the uuid are both TOLERATED (rc 0 on
    # an open lane, asserted in the positive control below). Reading these as
    # "usage errors" would be a false claim, so each asserts the closure refusal
    # and the empty stdout that makes it safe to consume.
    res = _run(run_tool, "claim-ref", W2, "--open")
    assert res.rc == 3, (
        "[claim-ref-open-closed-rc3] rc=%s, want 3 — W2's #999 was closed by the "
        "confirm above, so --open has no ref to act on\n%s"
        % (res.rc, res.combined[-600:]))
    assert not res.out.strip(), (
        "[claim-ref-open-closed-rc3] stdout=%r — a refusal must answer nothing, "
        "or oc-commit derives an Issue-Ref from a released claim" % (res.out,))

    res = _run(run_tool, "claim-ref", W2, "--open", "--open")
    assert res.rc == 3, (
        "[claim-ref-open-repeat-rc3] rc=%s, want 3 — repeating the flag must not "
        "change the closure verdict\n%s" % (res.rc, res.combined[-600:]))
    assert not res.out.strip(), (
        "[claim-ref-open-repeat-rc3] stdout=%r — a repeated flag must not make "
        "the verb answer where it refused" % (res.out,))

    res = _run(run_tool, "claim-ref", "--open", W2)
    assert res.rc == 3, (
        "[claim-ref-open-before-uuid-rc3] rc=%s, want 3 — flag position must not "
        "change the closure verdict\n%s" % (res.rc, res.combined[-600:]))
    assert not res.out.strip(), (
        "[claim-ref-open-before-uuid-rc3] stdout=%r — a flag before the uuid "
        "must not make the verb answer where it refused" % (res.out,))

    res = _run(run_tool, "claim-ref", W2, "--bogus")
    assert res.rc == 2, "[claim-ref-unknown-flag-rc2] rc=%s, want 2\n%s" % (
        res.rc, res.combined[-600:])
    res = _run(run_tool, "claim-ref", "--open")
    assert res.rc == 2, "[claim-ref-open-no-uuid-rc2] rc=%s, want 2\n%s" % (
        res.rc, res.combined[-600:])

    # POSITIVE CONTROL: the same verb answers for a live open claim, so the
    # refusals above cannot pass on a verb that never derives at all.
    res = _run(run_tool, "claim", "--issue", "5555",
               "--what", "fixture open for --open", env=_as(WC))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "claim-ref", WC, "--open")
    assert res.rc == 0, "[claim-ref-open-live-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert res.out.strip() == "5555", (
        "[claim-ref-open-live-value] stdout=%r, want '5555'" % (res.out,))

    # The tolerance claim in the comment above, ASSERTED rather than assumed:
    # the two "odd spellings" are accepted while the claim is OPEN, so their
    # rc 3 on W2 is the CLOSURE talking and nothing else. Without these two
    # arms the names above would be ambiguous between "rejected the syntax" and
    # "refused the closed claim".
    res = _run(run_tool, "claim-ref", WC, "--open", "--open")
    assert res.rc == 0 and res.out.strip() == "5555", (
        "a repeated --open on an OPEN claim gave rc=%s out=%r, want rc 0 / "
        "'5555' — if this ever becomes rc 3 the names above stop meaning what "
        "they say" % (res.rc, res.out))
    res = _run(run_tool, "claim-ref", "--open", WC)
    assert res.rc == 0 and res.out.strip() == "5555", (
        "--open before the uuid on an OPEN claim gave rc=%s out=%r, want rc 0 / "
        "'5555' — flag position is tolerated, so the W2 arms test closure"
        % (res.rc, res.out))

    res = _run(run_tool, "stamp", "done", "done #5555 — fixture release",
               env=_as(WC))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "claim-ref", WC, "--open")
    assert res.rc == 3, (
        "[claim-ref-open-released-rc3] rc=%s, want 3 — a done row released the "
        "claim, so there is no ref to act on\n%s" % (res.rc, res.combined[-600:]))
    res = _run(run_tool, "claim-ref", WC)
    assert res.out.strip() == "5555", (
        "[claim-ref-plain-ignores-closure] the plain form answered %r, want "
        "'5555' — closure changes --open only" % (res.out,))

def test_open_answers_the_newest_still_open_claim_not_the_newest_row(
        ledger_sandbox, run_tool):
    """``claim-ref-open-older-open-row-wins`` + ``claim-ref-open-older-open-rc0``
    + ``claim-ref-plain-still-latest-row`` + ``claim-ref-open-none-left-rc3``
    + ``claim-ref-open-none-left-diagnostic`` (#492).

    The exact shape that made the verb answer rc 3 for a lane that DOES hold an
    open claim: #8801 open, then #8802 claimed and CLOSED, so the newest row is
    closed while an older one is open. ``oc-commit`` derived no Issue-Ref and
    refused to commit (live instance: rc 3 while ``claims 318`` showed an open
    row).

    MUTATION KILL: restore the latest-row-only selection and the first two legs
    fail with an empty answer and rc 3.
    """
    res = _run(run_tool, "stamp", "claim", "CLAIM #8801 — older claim left open",
               env=_as(WO))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "stamp", "claim",
               "CLAIM #8802 — newer claim, closed below", env=_as(WO))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "stamp", "done",
               "done #8802 — closure of the NEWER claim", env=_as(WO))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])

    res = _run(run_tool, "claim-ref", WO, "--open")
    assert res.out.strip() == "8801", (
        "[claim-ref-open-older-open-row-wins] --open answered %r, want '8801' — "
        "the newest STILL-OPEN row, not the newest row (#492)" % (res.out,))
    assert res.rc == 0, "[claim-ref-open-older-open-rc0] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    res = _run(run_tool, "claim-ref", WO)
    assert res.out.strip() == "8802", (
        "[claim-ref-plain-still-latest-row] the plain form answered %r, want "
        "'8802' — it answers the latest row whether open or closed"
        % (res.out,))

    res = _run(run_tool, "stamp", "done",
               "done #8801 — now every claim row is closed", env=_as(WO))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])

    res = _run(run_tool, "claim-ref", WO, "--open")
    assert res.rc == 3 and not res.out.strip(), (
        "[claim-ref-open-none-left-rc3] want rc=3 with empty stdout, got rc=%s "
        "out=%r" % (res.rc, res.out))
    assert ("older claim row(s) by %s were also scanned and none is open" % WO) \
        in res.err, (
        "[claim-ref-open-none-left-diagnostic] stderr %r does not say the older "
        "rows were SCANNED — without that line the caller cannot tell 'none "
        "left' from 'never looked'" % (res.err[-400:],))

# =============================================================================
# 9. `--max-age-d` — an over-age claim is not a weaker answer (#631)
# =============================================================================
def test_max_age_refuses_stale_and_undecidable_claims_but_stays_opt_in(
        ledger_sandbox, run_tool, raw_ledger):
    """``claim-ref-age-fresh-answers`` + ``claim-ref-age-zero-unbounded``
    + ``claim-ref-age-absent-unbounded`` + ``claim-ref-age-missing-value-rc2``
    + ``claim-ref-age-equals-form-rc0`` + ``claim-ref-age-twodots-rc2``,
    plus the ``bad`` legs ``claim-ref-age-stale-rc3`` / ``-diagnostic`` /
    ``-offers-escape-hatch``, ``claim-ref-age-undecidable-rc3`` /
    ``-diagnostic`` and ``claim-ref-age-nonnumeric-rc2`` / ``-diagnostic`` /
    ``-names-the-value``.

    Measured incident (factory #311): ``oc-commit`` derived an Issue-Ref from a
    claim made 51.1 days earlier and the per-commit note landed on an unrelated
    OPEN issue on the fork. The bound is OPT-IN (0 = unbounded), so every
    existing consumer keeps its exact behaviour — which is what
    ``claim-ref-age-absent-unbounded`` pins: make the bound the DEFAULT and that
    leg reddens.

    Three fixtures, each the discriminating half of the other two: WA stale and
    never closed, WB claimed just now, WD's stamp UNPARSEABLE. UNDECIDABLE is
    not FRESH — a row whose age cannot be read is not evidence of freshness.
    """
    stale = "2020-01-01T00:00:00Z"
    doc = raw_ledger("wl631", [
        {"t": stale, "kind": "claim", "by": "editor %s" % WA,
         "what": "CLAIM #311 — abandoned long ago, never closed"},
        {"t": L.now_iso(), "kind": "claim", "by": "editor %s" % WB,
         "what": "CLAIM #3110 — claimed just now"},
        {"t": "not-a-timestamp", "kind": "claim", "by": "editor %s" % WD,
         "what": "CLAIM #3111 — undateable"},
    ], workers=[{"uuid": WA, "role": "editor"}, {"uuid": WB, "role": "editor"},
                {"uuid": WD, "role": "editor"}])
    env = {"OC_LEDGER": str(doc)}

    # (a) STALE under a bound -> refuse, answer nothing, and name the escape.
    res = _run(run_tool, "claim-ref", WA, "--open", "--max-age-d", "7", env=env)
    assert res.rc == 3 and not res.out.strip(), (
        "[claim-ref-age-stale-rc3] want rc=3 with empty stdout, got rc=%s "
        "out=%r" % (res.rc, res.out))
    assert "STALE" in res.err, (
        "[claim-ref-age-stale-diagnostic] stderr %r does not name the claim "
        "STALE — 'refused' with no reason reads as a ledger bug"
        % (res.err[-400:],))
    assert "--issue" in res.err, (
        "[claim-ref-age-stale-offers-escape-hatch] stderr %r does not offer "
        "--issue, so a lane with a legitimate old claim has no way forward"
        % (res.err[-400:],))

    # (b) POSITIVE CONTROL: the SAME bound on a FRESH claim must still answer.
    res = _run(run_tool, "claim-ref", WB, "--open", "--max-age-d", "7", env=env)
    assert res.out.strip() == "3110", (
        "[claim-ref-age-fresh-answers] answered %r, want '3110' — a leg that "
        "only ever refuses passes on a verb that never derives at all"
        % (res.out,))

    # (c) KNOB: 0 is unbounded, so the stale lane answers again. Without this
    #     the arm above could be red for ANY refusal, not the age.
    res = _run(run_tool, "claim-ref", WA, "--open", "--max-age-d", "0", env=env)
    assert res.out.strip() == "311", (
        "[claim-ref-age-zero-unbounded] answered %r, want '311'" % (res.out,))

    # (d) BACKWARD COMPAT: the bound is opt-in.
    res = _run(run_tool, "claim-ref", WA, "--open", env=env)
    assert res.out.strip() == "311", (
        "[claim-ref-age-absent-unbounded] an ABSENT flag answered %r, want "
        "'311' — this is the leg that reddens if the bound becomes the default, "
        "which would silently change every existing consumer" % (res.out,))

    # (e) UNDECIDABLE != FRESH.
    res = _run(run_tool, "claim-ref", WD, "--open", "--max-age-d", "7", env=env)
    assert res.rc == 3 and not res.out.strip(), (
        "[claim-ref-age-undecidable-rc3] want rc=3 with empty stdout, got rc=%s "
        "out=%r" % (res.rc, res.out))
    assert "UNDECIDABLE" in res.err, (
        "[claim-ref-age-undecidable-diagnostic] stderr %r does not say the age "
        "is UNDECIDABLE — reading an unparseable stamp as age 0 is fail-open on "
        "the exact path that writes a false trailer into history"
        % (res.err[-400:],))

    # (f) ARG VALIDATION: a flag that needs a value must say so, not read the
    #     next token as one (an accepted-but-inert bound is indistinguishable
    #     from an honoured one).
    res = _run(run_tool, "claim-ref", WB, "--open", "--max-age-d", env=env)
    assert res.rc == 2, (
        "[claim-ref-age-missing-value-rc2] rc=%s, want 2\n%s"
        % (res.rc, res.combined[-600:]))
    res = _run(run_tool, "claim-ref", WB, "--open", "--max-age-d=7", env=env)
    assert res.rc == 0, (
        "[claim-ref-age-equals-form-rc0] rc=%s, want 0 — the = form is the same "
        "flag\n%s" % (res.rc, res.combined[-600:]))

    # (g) NON-NUMERIC BOUND: `--max-age-d 7d` used to parse into max_age_d="7d"
    #     and then be read by the helper as 0 = UNBOUNDED.
    res = _run(run_tool, "claim-ref", WA, "--open", "--max-age-d", "7d", env=env)
    assert res.rc == 2 and not res.out.strip(), (
        "[claim-ref-age-nonnumeric-rc2] want rc=2 with empty stdout, got rc=%s "
        "out=%r" % (res.rc, res.out))
    assert "must be a number" in res.err, (
        "[claim-ref-age-nonnumeric-diagnostic] stderr %r does not say the bound "
        "must be a number" % (res.err[-400:],))
    assert "7d" in res.err, (
        "[claim-ref-age-nonnumeric-names-the-value] stderr %r does not quote "
        "the offending value, so a caller cannot see what was rejected"
        % (res.err[-400:],))
    res = _run(run_tool, "claim-ref", WA, "--open", "--max-age-d", "1.2.3",
               env=env)
    assert res.rc == 2, "[claim-ref-age-twodots-rc2] rc=%s, want 2\n%s" % (
        res.rc, res.combined[-600:])


# =============================================================================
# 10. `claims <N>` — the dispatch=verify-unclaimed backend
# =============================================================================
def test_claims_answers_open_rows_and_goes_clean_when_the_claim_closes(
        ledger_sandbox, run_tool):
    """``claims-open-rc`` + ``claims-clean-rc`` + ``claims-closed-rc``
    + ``claims-noarg-rc0`` + ``claims-nonnum-rc2``, plus the ``ok``/``bad`` legs
    ``claims-open-row``, ``claims-999-still-open-after-confirm``,
    ``claims-clean-not-empty`` and ``claims-closed-still-open``.

    Empty output + rc 0 IS the clean verdict — the grep-lane hand query,
    mechanized — so every arm reads the OUTPUT, not the rc. The #999 arm is the
    D-2 assertion in the direction that matters: after ``confirm`` ran, #999
    must no longer read OPEN, because the old selftest asserted the opposite and
    thereby pinned the defect (confirm wrote only to ``workers[].events``, a
    store ``cmd_claims`` never reads).
    """
    _enroll(run_tool, W2)
    res = _run(run_tool, "stamp", "claim", "CLAIM #999 — fixture claim for confirm",
               env=_as(W2))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])

    res = _run(run_tool, "stamp", "claim", "CLAIM #777 — fixture open claim",
               env=_as(W4))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])

    res = _run(run_tool, "claims", "777")
    assert res.rc == 0, "[claims-open-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert W4 in res.out and "#777" in res.out, (
        "[claims-open-row] claims 777 printed %r — want the row for %s on "
        "#777" % (res.out, W4))

    # A confirm closes #999 (a closing kind), so it must not read OPEN.
    res = _run(run_tool, "stamp", "confirm", "CONFIRM #999 — fixture closure",
               env=_as(W2))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "claims", "999")
    assert W2 not in res.out, (
        "[claims-999-still-open-after-confirm] claims 999 still prints %s — "
        "confirm must append the top-level row cmd_claims scans (D-2, HQ "
        "d72bd52d): %r" % (W2, res.out))

    res = _run(run_tool, "claims", "123456")
    assert res.rc == 0, "[claims-clean-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert not res.out.strip(), (
        "[claims-clean-not-empty] claims 123456 printed %r — an unclaimed issue "
        "must answer with nothing at all, not a header" % (res.out,))

    res = _run(run_tool, "stamp", "confirm",
               "CONFIRM #777 — fixture closure (confirm = closing kind in v1.1 "
               "vocabulary)", env=_as(W4))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "claims", "777")
    assert res.rc == 0, "[claims-closed-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert W4 not in res.out, (
        "[claims-closed-still-open] claims 777 still prints %s after a confirm "
        "closed it: %r" % (W4, res.out))

    res = _run(run_tool, "claims")
    assert res.rc == 0, "[claims-noarg-rc0] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    res = _run(run_tool, "claims", "abc")
    assert res.rc == 2, "[claims-nonnum-rc2] rc=%s, want 2\n%s" % (
        res.rc, res.combined[-600:])

@pytest.mark.parametrize("kind", ["close", "done", "unclaim", "reject"])
def test_every_documented_closing_kind_is_stampable_and_actually_closes(
        ledger_sandbox, run_tool, kind):
    """``closure-kind-$k-claim-rc`` + ``closure-kind-$k-stampable`` for
    ``k in {close, done, unclaim, reject}``, plus the ``bad`` leg
    ``closure-kind-$k-did-not-close``.

    D-2: KINDS carried none of close/done/unclaim/reject, so 4 of the 5
    documented closers were UNSTAMPABLE — ``stamp close #N`` died rc 2 and the
    contract ``cmd_claims`` documents was a dead letter by vocabulary (live
    impact: #150 and #191 both shipped and both still read OPEN). Each kind must
    therefore be stampable AND must actually close a claim; a loop that asserted
    only the rc would pass on four kinds that write a row nobody reads.

    One test per kind rather than one loop: the shell's ``for k in …`` body is
    the same three assertions four times, and as four separate legs a regression
    names the kind that broke instead of stopping at the first.
    """
    res = _run(run_tool, "stamp", "claim",
               "CLAIM #888 — fixture for kind %s" % kind, env=_as(W5))
    assert res.rc == 0, (
        "[closure-kind-%s-claim-rc] rc=%s, want 0\n%s"
        % (kind, res.rc, res.combined[-600:]))
    res = _run(run_tool, "stamp", kind, "%s #888 — fixture closure" % kind,
               env=_as(W5))
    assert res.rc == 0, (
        "[closure-kind-%s-stampable] rc=%s, want 0 — this kind is a "
        "documented closer, so an rc 2 here makes the contract a dead "
        "letter\n%s" % (kind, res.rc, res.combined[-600:]))

    res = _run(run_tool, "claims", "888")
    assert W5 not in res.out, (
        "[closure-kind-%s-did-not-close] a '%s' row left %s's claim on #888 "
        "OPEN: %r" % (kind, kind, W5, res.out))

def test_claims_matches_the_address_not_a_digit_run(
        ledger_sandbox, run_tool):
    """``claims-nohash-claim-rc`` + ``claims-nohash-rc`` +
    ``claims329-claim-rc``, plus ``claims-nohash-false-clean``,
    ``claims-76-matched-760``, ``claims-760-not-matched``,
    ``claims329-phantom-on-mentioned-issue``, ``claims329-addressed-issue-not-open``,
    ``claims329-structured-issues-field``, ``claims329-dual-claim-issues-field``
    and ``claims329-note-carries-no-issues-field``.

    Three defects in one family, and each arm is the other's control:

    * FALSE-CLEAN: the scan matched the ref as a substring of ``#N``, so a claim
      written ``issue=N`` (no hash) was INVISIBLE and ``claims N`` answered CLEAN
      for an issue that IS claimed.
    * FALSE POSITIVE: the same substring test made ``claims 76`` match a claim
      on ``#760``.
    * #329: a claim's TARGET is its ADDRESS, never every reference in the note.
      ``n=8226`` claims #327 and mentions ``(#323)``; reading the mention as a
      claim produced 13 phantom claims fleet-wide, one of which made the sweep
      want to write a false unclaim row.

    The structured ``issues`` field is what makes the third fix durable: the
    target is recorded at WRITE time rather than re-inferred from prose on every
    read, so a note (not a claim) must carry no ``issues`` field at all.
    """
    ledger = Path(ledger_sandbox.ledger)

    res = _run(run_tool, "stamp", "claim", CLAIM_NO_HASH, env=_as(W6))
    assert res.rc == 0, "[claims-nohash-claim-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    res = _run(run_tool, "claims", "4242")
    assert res.rc == 0, "[claims-nohash-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert W6 in res.out, (
        "[claims-nohash-false-clean] claims 4242 answered CLEAN for an issue "
        "that IS claimed — the 'issue=N' form carries no '#' and the scan must "
        "not depend on one: %r" % (res.out,))

    res = _run(run_tool, "stamp", "claim", CLAIM_SUBSTRING_TRAP, env=_as(W6))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "claims", "76")
    assert W6 not in res.out, (
        "[claims-76-matched-760] claims 76 matched the claim on #760 — a "
        "substring test makes every prefix of an issue number lie: %r"
        % (res.out,))
    res = _run(run_tool, "claims", "760")
    assert W6 in res.out, (
        "[claims-760-not-matched] claims 760 does not show the #760 claim, so "
        "the leg above passes on a scan that matches nothing: %r" % (res.out,))

    res = _run(run_tool, "stamp", "claim", CLAIM_MENTION, env=_as(W9))
    assert res.rc == 0, "[claims329-claim-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    res = _run(run_tool, "claims", "323")
    assert W9 not in res.out, (
        "[claims329-phantom-on-mentioned-issue] the #323 MENTION in the note "
        "registered a phantom claim — the row's address is #327: %r" % (res.out,))
    res = _run(run_tool, "claims", "327")
    assert W9 in res.out, (
        "[claims329-addressed-issue-not-open] claims 327 does not show the row "
        "that IS addressed to #327: %r" % (res.out,))

    assert _last_by(ledger, W9).get("issues") == [327], (
        "[claims329-structured-issues-field] the row's structured issues=%r, "
        "want [327] — the target is recorded at write time, not re-inferred "
        "from prose" % (_last_by(ledger, W9).get("issues"),))

    # A genuine dual claim keeps BOTH targets (live shape: n=4802
    # "CLAIM #193, #205").
    res = _run(run_tool, "stamp", "claim",
               "CLAIM #193, #205 — fixture dual claim", env=_as(W9))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    assert _last_by(ledger, W9).get("issues") == [193, 205], (
        "[claims329-dual-claim-issues-field] the dual claim's issues=%r, want "
        "[193, 205] — prose separates references, list punctuation does not"
        % (_last_by(ledger, W9).get("issues"),))

    # ...and a NOTE carries no issues field: the array is a claim's target, not
    # a general ref list (a note's references are not claims on anything).
    res = _run(run_tool, "stamp", "note",
               "note referencing #323 and #327", env=_as(W9))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    assert _last_by(ledger, W9).get("issues") is None, (
        "[claims329-note-carries-no-issues-field] the note row carries "
        "issues=%r, want none — a reference in a note is not a claim"
        % (_last_by(ledger, W9).get("issues"),))

# =============================================================================
# 11. the sentinel actors — unclosable claims get a closer, attributed ones do not
# =============================================================================
def test_unattributed_and_unrostered_claims_are_closable_but_attributed_ones_are_not(
        ledger_sandbox, run_tool, raw_ledger):
    """``claims-unrostered-rc`` plus ``claims-unattr-not-open``,
    ``claims-unattr-unclosable``, ``claims-attributed-closed-by-other-actor``,
    ``claims-unrostered-still-unclosable`` and
    ``claims-unrostered-label-unclosable``.

    A claim whose ``by`` is the unattributed sentinel could never close: the
    linker is ``contains($by)`` and no real closure carries that literal, so the
    actor test is DROPPED for a sentinel claim. The attributed fixture is the
    CONTROL — an ATTRIBUTED claim must still need its own actor, or "drop the
    actor test" would silently release every lane's claim on a foreign mention
    (#305). The ``unrostered-actor`` sentinel gets the same treatment as a
    PREFIX, which is what covers the malformed legacy labels
    (``unrostered-actor d5863180-editor``, ``… editor-141``).

    The sentinel is read from the tool's own source rather than hardcoded, so it
    cannot drift out of agreement with the writer.
    """
    sentinel = re.search(r"\(unattributed[^)]*\)",
                         TOOL.read_text(encoding="utf-8")).group(0)
    assert sentinel, "claims-fixture-sentinel-unresolved: no sentinel in the tool"

    def claims_on(ledger_path, issue):
        return _run(run_tool, "claims", issue, env={"OC_LEDGER": str(ledger_path)})

    open_doc = raw_ledger("uat-open", [
        {"n": 1, "t": "2026-09-12T00:00:00Z", "by": sentinel, "kind": "claim",
         "what": "CLAIM #5150 — unattributed fixture"}])
    res = claims_on(open_doc, "5150")
    assert "unattributed" in res.out, (
        "[claims-unattr-not-open] claims 5150 printed %r, want the unattributed "
        "row — an open sentinel claim must still read OPEN" % (res.out,))

    closed_doc = raw_ledger("uat-closed", [
        {"n": 1, "t": "2026-09-12T00:00:00Z", "by": sentinel, "kind": "claim",
         "what": "CLAIM #5150 — unattributed fixture"},
        {"n": 2, "t": "2026-09-12T00:01:00Z",
         "by": "editor %s" % W4, "kind": "confirm",
         "what": "CONFIRM #5150 — closure by another lane"}])
    res = claims_on(closed_doc, "5150")
    assert "unattributed" not in res.out, (
        "[claims-unattr-unclosable] a later closer referencing #5150 did NOT "
        "close the sentinel claim, so it is unclosable by construction: %r"
        % (res.out,))

    attr_doc = raw_ledger("uat-attr", [
        {"n": 1, "t": "2026-09-12T00:00:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "CLAIM #5151 — attributed fixture"},
        {"n": 2, "t": "2026-09-12T00:01:00Z",
         "by": "editor 22222222-2222-2222-2222-222222222222", "kind": "confirm",
         "what": "CONFIRM #5151 — closure by a DIFFERENT lane"}])
    res = claims_on(attr_doc, "5151")
    assert "11111111" in res.out, (
        "[claims-attributed-closed-by-other-actor] a DIFFERENT lane's confirm "
        "released an attributed claim — the actor test is the fence that stops "
        "a foreign prose mention from releasing live work (#305): %r"
        % (res.out,))

    unrostered_doc = raw_ledger("uat-unrostered", [
        {"n": 1, "t": "2026-09-12T00:00:00Z",
         "by": "unrostered-actor 99999999-9999-9999-9999-999999999999",
         "kind": "claim", "what": "CLAIM #5152 — unrostered-actor fixture"},
        {"n": 2, "t": "2026-09-12T00:01:00Z", "by": "editor %s" % W4,
         "kind": "confirm",
         "what": "CONFIRM #5152 — closure by the now-rostered lane"}])
    res = claims_on(unrostered_doc, "5152")
    assert res.rc == 0, "[claims-unrostered-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert not res.out.strip(), (
        "[claims-unrostered-still-unclosable] the unrostered-actor claim is "
        "still open after a natural closer — its rows could otherwise only be "
        "closed by hand-reproducing the historical `by` string: %r" % (res.out,))

    # ...and the sentinel is matched as a PREFIX, so the malformed legacy
    # labels are covered by the same arm.
    legacy_doc = raw_ledger("uat-unrostered2", [
        {"n": 1, "t": "2026-09-12T00:00:00Z",
         "by": "unrostered-actor d5863180-editor", "kind": "claim",
         "what": "CLAIM #5153 — malformed legacy label"},
        {"n": 2, "t": "2026-09-12T00:01:00Z", "by": "editor %s" % W4,
         "kind": "confirm", "what": "CONFIRM #5153 — closure"}])
    res = claims_on(legacy_doc, "5153")
    assert not res.out.strip(), (
        "[claims-unrostered-label-unclosable] the malformed legacy label "
        "'unrostered-actor d5863180-editor' was not treated as the sentinel: %r"
        % (res.out,))

# =============================================================================
# 12. lessons — extraction by kind and class
# =============================================================================
def test_lessons_filters_by_kind_and_matches_class_as_a_substring(
        ledger_sandbox, run_tool):
    """``lessons-lesson-rc`` + ``lessons-class-rc`` + ``lessons-bad-kind-rc2``
    + ``lessons-invalidregex-clean``, plus ``lessons-lesson-row``,
    ``lessons-wrong-kind-leak``, ``lessons-class-match``,
    ``lessons-invalidregex-empty`` and ``lessons-case-insensitive``.

    F-4 (v0.4.119): ``--class`` is a SUBSTRING match, not a regex. The old
    ``test($cls;"i")`` compiled it as regex, so an invalid regex hit jq's
    stderr-to-/dev/null plus an unconditional exit 0 — a SILENT false-clean on
    the sweep that exists to find uncoded lessons. The invalid-regex leg
    therefore asserts both the rc and the EMPTINESS: rc 0 alone would pass on a
    verb that returned everything.
    """
    res = _run(run_tool, "stamp", "lesson",
               "LESSON-FIXTURE uncoded gate-bypass lesson", env=_as(W4))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])
    res = _run(run_tool, "stamp", "incident",
               "INCIDENT-FIXTURE phantom write without receipt", env=_as(W4))
    assert res.rc == 0, "precondition: rc=%s\n%s" % (res.rc, res.combined[-600:])

    res = _run(run_tool, "lessons", "--kind", "lesson")
    assert res.rc == 0, "[lessons-lesson-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert "LESSON-FIXTURE" in res.out, (
        "[lessons-lesson-row] --kind lesson printed %r, want the lesson row"
        % (res.out,))
    assert "INCIDENT-FIXTURE" not in res.out, (
        "[lessons-wrong-kind-leak] --kind lesson also printed the INCIDENT row: "
        "%r" % (res.out,))

    res = _run(run_tool, "lessons", "--kind", "all", "--class", "phantom")
    assert res.rc == 0, "[lessons-class-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert "phantom" in res.out, (
        "[lessons-class-match] --class phantom printed %r, want the incident "
        "row that carries the word" % (res.out,))

    res = _run(run_tool, "lessons", "--kind", "bogus")
    assert res.rc == 2, "[lessons-bad-kind-rc2] rc=%s, want 2\n%s" % (
        res.rc, res.combined[-600:])

    res = _run(run_tool, "lessons", "--class", "[patch-id")
    assert res.rc == 0, (
        "[lessons-invalidregex-clean] rc=%s, want 0 — an invalid regex is a "
        "clean rc-0 substring miss, not a crash\n%s"
        % (res.rc, res.combined[-600:]))
    assert not res.out.strip(), (
        "[lessons-invalidregex-empty] the invalid-regex query printed %r — a "
        "regex that fails to compile must match NOTHING, not everything"
        % (res.out,))

    res = _run(run_tool, "lessons", "--class", "GATE-BYPASS")
    assert "LESSON-FIXTURE" in res.out, (
        "[lessons-case-insensitive] --class GATE-BYPASS did not match "
        "'gate-bypass': %r" % (res.out,))


# =============================================================================
# 13. sweep-closed-claims — the token scan, and the mention that is not a claim
# =============================================================================
# The three home trackers, as the sweep's probe spells them. A rule matches on a
# SUBSTRING of the joined argv, and first match wins, so the factory and binary
# rules go FIRST: ``leshchenko1979/opencrabs`` is a prefix of
# ``leshchenko1979/opencrabs-dev-factory``.
FORK = "leshchenko1979/opencrabs"
FACTORY = "leshchenko1979/opencrabs-dev-factory"
BINARY = "opencrabs/opencrabs"

def _json_issues(*pairs) -> str:
    return json.dumps([{"number": n, "title": t} for n, t in pairs])

# The shell's repo-aware, state-aware stub. The data is deliberate:
#   FORK    closed {29,49,52,55,126,80,64}  open {38,63}
#   FACTORY closed {77,64}                  open {55}
#   BINARY  (none)
# #55 is the fail-safe discriminator (closed on the fork, OPEN on the factory)
# and #64 the OVERLAP discriminator (closed on both, DIFFERENT title on each).
TRACKER_RULES = [
    (FACTORY + " --state closed",
     _json_issues((77, "factory-closed"), (64, "factory-sixtyfour")), 0),
    (FACTORY + " --state open", _json_issues((55, "factory-open")), 0),
    (BINARY + " --state closed", "[]", 0),
    (BINARY + " --state open", "[]", 0),
    (FORK + " --state closed",
     _json_issues((29, "compaction"), (49, "cap"), (52, "row-budget"),
                  (55, "fork-closed"), (126, "ontology"), (80, "bg-resume"),
                  (64, "fork-sixtyfour")), 0),
    (FORK + " --state open",
     _json_issues((38, "bg-resume-half"), (63, "open fork issue")), 0),
]

# The write-path stub: STATE-aware only (it answers the same list for every
# repo). Harmless for this block because the probe applies OPEN WINS, so a stub
# that reported 61/62 as OPEN would correctly refuse to release them and the
# block would fail for the RIGHT reason. 63 is the genuinely-open control.
WRITE_RULES = [
    ("--state closed", _json_issues((61, "stale-a"), (62, "stale-b")), 0),
    ("--state open", _json_issues((63, "still-open")), 0),
]

def _sweep(run_tool, ledger_path, *args):
    return _run(run_tool, "sweep-closed-claims", *args,
                env={"OC_LEDGER": str(ledger_path)})

def test_the_sweep_extracts_tokens_by_address_and_ignores_a_prose_mention(
        ledger_sandbox, run_tool, raw_ledger, gh_stub):
    r"""``sweep-closed-claims-rc`` + ``sweep-date-prefix-token-extracted``
    + ``sweep-gh-handle-token-extracted`` + ``sweep-prose-mention-not-a-claim``
    + ``sweep-uuid-prefix-token-extracted`` + ``sweep-multi-ref-token-extracted``
    + ``sweep-closed-half-multi-ref-flagged`` (#272, anchored by #329).

    Five row shapes, each of which a naive ``#?(\d+)`` scan gets WRONG: a date
    (``2026-08-27``), a GitHub handle (``leshchenko1979/opencrabs#52``), a
    session-uuid prefix (``6630dc9a-0eeb``), a multi-ref claim (``#38, #80``)
    whose first half is closed by a later row, and — the #329 half — a row that
    claims #52 and merely MENTIONS ``#49``.

    ``sweep-prose-mention-not-a-claim`` is the discriminating leg: the old
    assertion demanded #49 be released, which is precisely the phantom-claim
    defect #329 removes. #52 is in the mock's closed list so the row still
    proves the HANDLE form is extracted under the anchored rule.
    """
    doc = raw_ledger("sweep_fixture", [
        {"n": 1, "t": "2026-09-12T00:00:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "Claimed compaction-signal feature 2026-08-27 #29 #1256"},
        {"n": 2, "t": "2026-09-12T00:00:00Z",
         "by": "editor 22222222-2222-2222-2222-222222222222", "kind": "claim",
         "what": "claim leshchenko1979/opencrabs#52 row-budget share #49"},
        {"n": 3, "t": "2026-09-12T00:00:00Z",
         "by": "unrostered-actor 6630dc9a-0eeb-46c2-95b8-000000000000",
         "kind": "claim", "what": "CLAIM #126 session 6630dc9a-0eeb"},
        {"n": 4, "t": "2026-09-12T00:00:00Z",
         "by": "editor 33333333-3333-3333-3333-333333333333", "kind": "claim",
         "what": "CLAIM #38, #80 — bg-resume multi-ref"},
        {"n": 5, "t": "2026-09-12T00:01:00Z",
         "by": "editor 33333333-3333-3333-3333-333333333333", "kind": "close",
         "what": "CLOSE #38 — half closed"},
    ])
    gh_stub(rules=TRACKER_RULES, default_rc=1)

    res = _sweep(run_tool, doc)
    assert res.rc == 0, "[sweep-closed-claims-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-1000:])

    for name, needle in (
            ("sweep-date-prefix-token-extracted", "Issue #29 (CLOSED: compaction)"),
            ("sweep-gh-handle-token-extracted", "Issue #52 (CLOSED: row-budget)"),
            ("sweep-uuid-prefix-token-extracted", "Issue #126 (CLOSED: ontology)"),
            ("sweep-multi-ref-token-extracted", "Issue #80 (CLOSED: bg-resume)")):
        assert needle in res.out, (
            "[%s] stdout does not contain %r — a date, a handle, a uuid prefix "
            "and a multi-ref must each yield their issue and no extra digits: "
            "%r" % (name, needle, res.out))

    assert "Issue #49" not in res.out, (
        "[sweep-prose-mention-not-a-claim] the sweep flagged #49, which the row "
        "only MENTIONS — it claims #52. This is the phantom-claim defect #329 "
        "removes: %r" % (res.out,))
    assert "Issue #38 " not in res.out, (
        "[sweep-closed-half-multi-ref-flagged] #38 was closed by event 5, so it "
        "must not be flagged — a scan that ignores closure would release a live "
        "claim on a half-closed multi-ref: %r" % (res.out,))

def test_an_unresolvable_token_is_reported_and_withholds_the_clean_verdict(
        ledger_sandbox, run_tool, raw_ledger, gh_stub):
    """``sweep-unresolved-rc`` + ``sweep-unresolved-class-reported``
    + ``sweep-unresolved-names-the-token`` + ``sweep-unresolved-false-clean-verdict``
    + ``sweep-unresolved-over-reports-open-issues``
    + ``sweep-unresolved-writes-nothing`` (#485).

    Before this fix the scan compared tokens against the CLOSED list only, so
    three states collapsed into one: an OPEN issue (the intended clean case), an
    issue that does not exist, and an upstream-qualified ref read in fork space.
    All three printed "All open claims map to OPEN issues." — which is how
    n=1678 stayed OPEN for 15 days against work that had shipped.

    MUTATION KILL: restore the closed-list-only scan and the false-clean leg
    fails with the very line the incident was about.
    """
    doc = raw_ledger("sweep_unres", [
        {"n": 1, "t": "2026-09-21T00:00:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "CLAIM #1419 — upstream-qualified ref read in fork space"},
        {"n": 2, "t": "2026-09-21T00:00:01Z",
         "by": "editor 22222222-2222-2222-2222-222222222222", "kind": "claim",
         "what": "CLAIM #63 — a genuinely OPEN fork issue"},
    ])
    gh_stub(rules=TRACKER_RULES, default_rc=1)

    res = _sweep(run_tool, doc)
    assert res.rc == 0, "[sweep-unresolved-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-1000:])
    assert "UNRESOLVED: 1 claim token(s)" in res.out, (
        "[sweep-unresolved-class-reported] stdout %r does not report exactly "
        "one UNRESOLVED token — the third class is what makes the verdict a "
        "claim about a population" % (res.out,))
    assert "Issue #1419 is on no home tracker" in res.out, (
        "[sweep-unresolved-names-the-token] the report does not name #1419, so "
        "the operator cannot act on it: %r" % (res.out,))
    assert "All open claims map to OPEN issues" not in res.out, (
        "[sweep-unresolved-false-clean-verdict] the clean verdict was printed "
        "while an unresolvable token is in the population — this is the exact "
        "line that lied for 15 days: %r" % (res.out,))
    assert "Issue #63 is on no home tracker" not in res.out, (
        "[sweep-unresolved-over-reports-open-issues] #63 is genuinely OPEN and "
        "was reported unresolvable — a blanket class is not a fix: %r"
        % (res.out,))

    assert L.where(doc, kind="unclaim") == [], (
        "[sweep-unresolved-writes-nothing] the sweep wrote %d unclaim row(s) — "
        "an unresolvable token is not a licence to write"
        % len(L.where(doc, kind="unclaim")))

def test_the_clean_verdict_is_printed_with_the_population_it_claims(
        ledger_sandbox, run_tool, raw_ledger, gh_stub):
    """``sweep-clean-rc`` + ``sweep-clean-verdict-with-population``
    + ``sweep-clean-false-unresolved`` (#485 positive control).

    Without this, a fix that never printed the verdict would pass the
    unresolvable block VACUOUSLY. The four counts travel with the verdict so the
    claim can be checked against the population it names.
    """
    doc = raw_ledger("sweep_clean", [
        {"n": 1, "t": "2026-09-21T00:00:00Z",
         "by": "editor 33333333-3333-3333-3333-333333333333", "kind": "claim",
         "what": "CLAIM #63 — a genuinely OPEN fork issue"},
    ])
    gh_stub(rules=TRACKER_RULES, default_rc=1)

    res = _sweep(run_tool, doc)
    assert res.rc == 0, "[sweep-clean-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-1000:])
    assert "All open claims map to OPEN issues (1 1 0 0 =" in res.out, (
        "[sweep-clean-verdict-with-population] stdout %r does not carry the "
        "verdict with its four counts (claim rows, open, closed, unresolvable)"
        % (res.out,))
    assert "UNRESOLVED" not in res.out, (
        "[sweep-clean-false-unresolved] an all-OPEN population was reported as "
        "UNRESOLVED: %r" % (res.out,))

# =============================================================================
# 14. sweep-closed-claims — the WRITE path (#314)
# =============================================================================
def test_dry_run_writes_nothing_and_the_live_sweep_writes_one_row_per_issue(
        ledger_sandbox, run_tool, raw_ledger, gh_stub):
    """``sweep-dry-run-rc`` + ``sweep-live-rc`` + ``sweep-live-two-unclaims``
    + ``sweep-live-addressed`` + ``sweep-live-dedup-by-issue``
    + ``sweep-claims-61-rc``, plus ``sweep-dry-run-receipt``,
    ``sweep-dry-run-mutated-ledger``, ``sweep-live-row-count``,
    ``sweep-61-still-open``, ``sweep-62-still-open`` and
    ``sweep-open-issue-claim-released`` (#314).

    Before this fix the verb had NO write path: ``--dry-run`` was parsed, passed
    to the embedded scan, and the live branch printed the SAME scan and exited
    0 — so the flag changed nothing, and the selftest pinned that no-op as
    correct. The flag must now be load-bearing in BOTH directions, and the write
    must be ONE addressed ``unclaim`` row per CLOSED issue, DEDUPED across lanes
    (two lanes claim #61; one addressed row releases both), leaving the claim on
    the genuinely OPEN issue alone.
    """
    doc = raw_ledger("sweep_write", [
        {"n": 1, "t": "2026-09-18T00:00:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "CLAIM #61 — stale, lane A"},
        {"n": 2, "t": "2026-09-18T00:00:01Z",
         "by": "editor 22222222-2222-2222-2222-222222222222", "kind": "claim",
         "what": "CLAIM #61 — stale, lane B"},
        {"n": 3, "t": "2026-09-18T00:00:02Z",
         "by": "editor 33333333-3333-3333-3333-333333333333", "kind": "claim",
         "what": "CLAIM #62 — stale, lane C"},
        {"n": 4, "t": "2026-09-18T00:00:03Z",
         "by": "editor 33333333-3333-3333-3333-333333333333", "kind": "claim",
         "what": "CLAIM #63 — claim on an OPEN issue"},
    ])
    gh_stub(rules=WRITE_RULES, default_rc=1)

    before = len(L.events(doc))
    res = _sweep(run_tool, doc, "--dry-run")
    assert res.rc == 0, "[sweep-dry-run-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-1000:])
    assert "--dry-run: no ledger rows written" in res.out, (
        "[sweep-dry-run-receipt] the dry run did not SAY it wrote nothing, so "
        "the caller cannot tell a dry run from a live one: %r" % (res.out,))
    after_dry = len(L.events(doc))
    assert after_dry == before, (
        "[sweep-dry-run-mutated-ledger] the dry run changed the event count "
        "%d -> %d — --dry-run must be a no-op on the record"
        % (before, after_dry))

    res = _sweep(run_tool, doc)
    assert res.rc == 0, "[sweep-live-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-1000:])

    after = len(L.events(doc))
    assert after == before + 2, (
        "[sweep-live-row-count] want %d events, got %d — exactly one row per "
        "CLOSED issue (two issues), not one per claim (three)"
        % (before + 2, after))

    unclaims = L.where(doc, kind="unclaim")
    assert len(unclaims) == 2, (
        "[sweep-live-two-unclaims] the sweep wrote %d unclaim row(s), want 2"
        % len(unclaims))
    addressed = [e for e in unclaims
                 if (e.get("what") or "").startswith("#")
                 and "closed-issue stale claim sweep" in (e.get("what") or "")]
    assert len(addressed) == 2, (
        "[sweep-live-addressed] %d of 2 unclaim rows are ADDRESSED to their "
        "issue ('#N — closed-issue stale claim sweep'); an unaddressed row "
        "releases nothing, because signal 2 keys on the leading reference"
        % len(addressed))
    assert len({(e.get("what") or "")[:3] for e in unclaims}) == 2, (
        "[sweep-live-dedup-by-issue] the unclaim rows name %r — two lanes claim "
        "#61 and ONE row must release both, so the rows must be deduped by issue"
        % ([e.get("what") for e in unclaims],))

    res = _run(run_tool, "claims", "61", env={"OC_LEDGER": str(doc)})
    assert res.rc == 0, "[sweep-claims-61-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert not res.out.strip(), (
        "[sweep-61-still-open] #61 still reads OPEN after the sweep released it "
        "— the addressed row must close EVERY lane's claim on it: %r" % (res.out,))
    res = _run(run_tool, "claims", "62", env={"OC_LEDGER": str(doc)})
    assert not res.out.strip(), (
        "[sweep-62-still-open] #62 still reads OPEN after the sweep: %r"
        % (res.out,))
    res = _run(run_tool, "claims", "63", env={"OC_LEDGER": str(doc)})
    assert "33333333" in res.out, (
        "[sweep-open-issue-claim-released] the claim on the OPEN issue #63 was "
        "released — a sweep may only release what is closed everywhere: %r"
        % (res.out,))

# =============================================================================
# 15. three trackers, overlapping number spaces (v0.4.284)
# =============================================================================
def test_the_sweep_asks_every_tracker_and_open_anywhere_wins(
        ledger_sandbox, run_tool, raw_ledger, gh_stub):
    """``sweep-cross-rc`` + ``sweep-cross-releases-factory-closed``
    + ``sweep-cross-released-open-elsewhere-claim`` + ``sweep-cross-unresolved-count``
    + ``sweep-cross-unresolved-named`` + ``sweep-cross-false-clean-verdict``
    + ``sweep-cross-released-77`` + ``sweep-cross-55-claim-survived``.

    The pre-split probe only ever asked the fork, so a claim whose issue moved to
    the factory/upstream tracker read "still open" forever; the naive repair
    ("closed on any tracker") is WORSE, because it releases a live claim on the
    strength of an unrelated repo's issue number. #77 is the release leg; #55 —
    CLOSED on the fork, OPEN on the factory — is the discriminator, and a
    ``closed-anywhere`` implementation fails it.
    """
    doc = raw_ledger("sweep_cross", [
        {"n": 1, "t": "2026-10-03T00:00:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "CLAIM #77 — closed on the factory tracker only"},
        {"n": 2, "t": "2026-10-03T00:00:01Z",
         "by": "editor 22222222-2222-2222-2222-222222222222", "kind": "claim",
         "what": "CLAIM #55 — closed on the fork, OPEN on the factory"},
        {"n": 3, "t": "2026-10-03T00:00:02Z",
         "by": "editor 33333333-3333-3333-3333-333333333333", "kind": "claim",
         "what": "CLAIM #99 — on no home tracker"},
    ])
    gh_stub(rules=TRACKER_RULES, default_rc=1)

    res = _sweep(run_tool, doc)
    assert res.rc == 0, "[sweep-cross-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-1000:])
    assert "Issue #77 (CLOSED: factory-closed)" in res.out, (
        "[sweep-cross-releases-factory-closed] stdout %r does not release #77, "
        "which is closed on the FACTORY tracker — the probe must ask all three"
        % (res.out,))
    assert "Issue #55 (CLOSED" not in res.out, (
        "[sweep-cross-released-open-elsewhere-claim] #55 was released on the "
        "strength of the fork's closed issue while it is OPEN on the factory — "
        "OPEN ANYWHERE WINS, and this is the direction that writes a false "
        "unclaim: %r" % (res.out,))
    assert "UNRESOLVED: 1 claim token(s)" in res.out, (
        "[sweep-cross-unresolved-count] stdout %r does not report exactly one "
        "unresolvable token" % (res.out,))
    assert "Issue #99 is on no home tracker" in res.out, (
        "[sweep-cross-unresolved-named] the unresolvable token is not named: %r"
        % (res.out,))
    assert "All open claims map to OPEN issues" not in res.out, (
        "[sweep-cross-false-clean-verdict] the clean verdict was printed beside "
        "an unresolvable token: %r" % (res.out,))

    res = _run(run_tool, "claims", "77", env={"OC_LEDGER": str(doc)})
    assert res.out.strip() == "", (
        "[sweep-cross-released-77] claims 77 still prints %r — the release "
        "verdict must be visible in the scanner" % (res.out,))
    res = _run(run_tool, "claims", "55", env={"OC_LEDGER": str(doc)})
    assert "22222222" in res.out, (
        "[sweep-cross-55-claim-survived] the claim on #55 did not survive: %r"
        % (res.out,))

def test_an_overlapping_number_keeps_its_release_verdict_but_loses_its_title(
        ledger_sandbox, run_tool, raw_ledger, gh_stub):
    """``sweep-overlap-rc`` + ``sweep-overlap-single-tracker-title-kept``
    + ``sweep-overlap-prints-fork-title`` + ``sweep-overlap-prints-factory-title``
    + ``sweep-overlap-ambiguity-named`` + ``sweep-overlap-names-the-count``
    + ``sweep-overlap-released-64`` + ``sweep-overlap-29-still-open`` (#38).

    The shape that hid #38: a number CLOSED on TWO home trackers, where the
    release verdict is unambiguous but the TITLE is not. ``probe()`` keeps the
    FIRST-probed repo title (the fork, since HOME_REPOS is fork-first) and the
    emit used to print it, so a factory claim on #33 was reported as the fork's
    #33 title. The claim token is a bare int (``parse_issue_ref_value`` DISCARDS
    the slug), so the token names no repo and NO title may be printed.

    #29 (fork-only) is the in-run positive control, so a fix that withheld EVERY
    title fails here rather than passing vacuously.
    """
    doc = raw_ledger("sweep_overlap", [
        {"n": 1, "t": "2026-10-14T00:00:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "CLAIM #64 — closed on BOTH the fork and the factory"},
        {"n": 2, "t": "2026-10-14T00:00:01Z",
         "by": "editor 22222222-2222-2222-2222-222222222222", "kind": "claim",
         "what": "CLAIM #29 — closed on the fork alone"},
    ])
    gh_stub(rules=TRACKER_RULES, default_rc=1)

    res = _sweep(run_tool, doc)
    assert res.rc == 0, "[sweep-overlap-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-1000:])

    assert "Issue #29 (CLOSED: compaction)" in res.out, (
        "[sweep-overlap-single-tracker-title-kept] a number seen on exactly ONE "
        "home tracker lost its title — the withholding must be specific to the "
        "overlap, or the fix reddens the normal case: %r" % (res.out,))
    assert "fork-sixtyfour" not in res.out, (
        "[sweep-overlap-prints-fork-title] the fork's #64 title was printed for "
        "a bare token that names no repo (first-probed wins is the pre-#38 "
        "emit): %r" % (res.out,))
    assert "factory-sixtyfour" not in res.out, (
        "[sweep-overlap-prints-factory-title] the factory's #64 title was "
        "printed — equally unsupported: %r" % (res.out,))
    assert "no single title" in res.out, (
        "[sweep-overlap-ambiguity-named] the emit withheld the title but did "
        "not SAY why: %r" % (res.out,))
    assert "2 home trackers" in res.out, (
        "[sweep-overlap-names-the-count] the ambiguity line does not name the "
        "number of trackers that carried #64: %r" % (res.out,))

    res = _run(run_tool, "claims", "64", env={"OC_LEDGER": str(doc)})
    assert res.out.strip() == "", (
        "[sweep-overlap-released-64] claims 64 still prints %r — closed "
        "everywhere and open nowhere IS a release, whatever the title: %r"
        % (res.out, res.out))
    res = _run(run_tool, "claims", "29", env={"OC_LEDGER": str(doc)})
    assert not res.out.strip(), (
        "[sweep-overlap-29-still-open] #29 was not released: %r" % (res.out,))

# =============================================================================
# 16. cross-lane standdown closure (#313)
# =============================================================================
def test_a_standdown_row_closes_another_lanes_claim_but_prose_does_not(
        ledger_sandbox, run_tool, raw_ledger):
    """``claims-standdown-rc`` + ``claims-standdown-did-not-close``
    + ``claims-foreign-prose-released-claim`` (#313, canonical rule signal 2).

    ``STANDDOWN #N (<uuid>) — …`` is stamped by a DIFFERENT lane (Triage stands
    a claim down on the claimant's behalf), so an author test alone closed
    nothing: the claim stayed OPEN until its claimant hand-stamped a redundant
    row (live n=7803 / n=8055). The NEGATIVE half is the #305 fence: a foreign
    row that merely MENTIONS ``#N`` in prose must NOT release another lane's
    claim — that is the whole point of anchoring the address at the start of
    ``what``.
    """
    doc = raw_ledger("standdown", [
        {"n": 1, "t": "2026-09-18T00:00:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "CLAIM #71 — stood down by another lane"},
        {"n": 2, "t": "2026-09-18T00:01:00Z",
         "by": "triage 22222222-2222-2222-2222-222222222222", "kind": "done",
         "what": "STANDDOWN #71 (11111111) — shipped and verified, claim released"},
        {"n": 3, "t": "2026-09-18T00:02:00Z",
         "by": "editor 11111111-1111-1111-1111-111111111111", "kind": "claim",
         "what": "CLAIM #72 — foreign prose mention must not release"},
        {"n": 4, "t": "2026-09-18T00:03:00Z",
         "by": "triage 22222222-2222-2222-2222-222222222222", "kind": "unclaim",
         "what": "UNCLAIM #72 — stood down in favour of editor lane 11111111"},
    ])

    res = _run(run_tool, "claims", "71", env={"OC_LEDGER": str(doc)})
    assert res.rc == 0, "[claims-standdown-rc] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert not res.out.strip(), (
        "[claims-standdown-did-not-close] the addressed STANDDOWN row did not "
        "close #71, so a stood-down claim stays OPEN until its claimant "
        "hand-stamps a redundant row: %r" % (res.out,))

    res = _run(run_tool, "claims", "72", env={"OC_LEDGER": str(doc)})
    assert "11111111" in res.out, (
        "[claims-foreign-prose-released-claim] a foreign row that only MENTIONS "
        "#72 released 11111111's claim — the fence #305 exists for: %r"
        % (res.out,))

# =============================================================================
# 17. the two kind-admission regressions (notify-fanout, shipchain)
# =============================================================================
def test_notify_fanout_and_shipchain_kinds_are_accepted_and_land(
        ledger_sandbox, run_tool):
    """``notify-fanout-kind-accepted`` + ``shipchain-kind-accepted``
    + ``shipchain-what-preserved`` + ``shipchain-no-prefix-match``, plus
    ``notify-fanout-row-on-ledger`` and ``shipchain-row-on-ledger``.

    Both kinds were absent from the enum, and in both cases the failure was
    SILENT: wave completions fell back to note-row workarounds, and 216/216
    ``oc-ship`` journal stamps died rc 2 under ``|| true``, so no chain ever had
    a ledger trail. The rc alone would not have caught it either — the row must
    LAND and keep its payload, which is what makes the chain id greppable. The
    typo arm is the control: a prefix match would accept ``shipchai``.
    """
    ledger = Path(ledger_sandbox.ledger)

    res = _run(run_tool, "stamp", "notify-fanout",
               "fanout 'T': sent=1 skipped=0 failed=0 ids: 99999999",
               env=_as(W4))
    assert res.rc == 0, "[notify-fanout-kind-accepted] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    assert L.where(ledger, kind="notify-fanout"), (
        "[notify-fanout-row-on-ledger] rc 0 but no notify-fanout row landed")

    res = _run(run_tool, "stamp", "shipchain",
               "[CHAIN-abc12345-20260911T000000Z] LEG1 gate GREEN", env=_as(W4))
    assert res.rc == 0, "[shipchain-kind-accepted] rc=%s, want 0\n%s" % (
        res.rc, res.combined[-600:])
    rows = L.where(ledger, kind="shipchain")
    assert rows, "[shipchain-row-on-ledger] rc 0 but no shipchain row landed"
    assert rows[-1]["what"].startswith("[CHAIN-abc12345-"), (
        "[shipchain-what-preserved] the stored text is %r, want it to start "
        "'[CHAIN-abc12345-' — the chain id is what makes a chain's trail "
        "greppable" % (rows[-1].get("what"),))

    res = _run(run_tool, "stamp", "shipchai", "x")
    assert res.rc == 2, (
        "[shipchain-no-prefix-match] rc=%s, want 2 — the kind vocabulary is "
        "exact, so a prefix match would let a typo mint a row no reader scans\n%s"
        % (res.rc, res.combined[-600:]))

