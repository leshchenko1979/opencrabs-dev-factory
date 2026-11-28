"""Ported: ``oc-ledger`` selftest §34-40 — attribution, ``derive_by`` and ``--by``.

Source: ``tools/state/oc-ledger:4007-4100`` (selftest lines 1237-1330) — 41
``chk`` calls. Every assertion message carries the shell name it replaces.

WHAT THIS MODULE PROTECTS — who a row is attributed to, and the three ways a
ledger ends up lying about it

1. AN ANONYMOUS ROW IS REFUSED (#19). Warn-and-write made the defect the
   default: every caller that forgot an actor still produced a row, and the row
   read as legitimate. The refusal must name ALL THREE remedies — ``--by``,
   ``OC_ACTOR``, ``--allow-unattributed`` — because a refusal that names one
   leaves the operator guessing at the other two, and it must WRITE NOTHING,
   because a refusal that still stamps is a warn in disguise.

2. THE DERIVATION LADDER RESOLVES, NEVER INVENTS. ``OC_ACTOR`` may be a full
   uuid, a SESSION id, a roster uuid, a unique uuid PREFIX, or a composed
   ``<role> <uuid>`` form. Each resolves to the roster's ``role + full uuid``.
   When nothing matches, the row keeps an HONEST sentinel
   (``unrostered-actor …``) rather than a guessed identity — and the sentinel is
   IDEMPOTENT, because feeding a prior row's ``by`` back in is the natural
   caller pattern and a second prefix would corrupt it.

   An AMBIGUOUS prefix must NOT resolve. A wrong pick is worse than an honest
   sentinel: it silently attributes a lane's work to a different lane, and
   nothing downstream can tell.

3. THE ``--by`` FLAG BYPASSES ``derive_by``, SO IT NEEDS ITS OWN GUARD (#320).
   ``--by`` writes verbatim, which is correct — HQ stamps
   ``hq/opencrabs-dev-factory`` and refusing a label would break it outright —
   but a hand-assembled uuid (remembered prefix + invented tail) landed as a
   phantom actor indistinguishable from a real one (row n=10499). The fix is a
   WARNING, not a refusal: 64 of 86 sentinel rows belong to uuids rostered TODAY,
   stamped inside the pre-enroll window, so refusing on shape would be wrong.

   Both controls are asserted, because each alone is satisfiable by a broken
   implementation: a LABEL must stay silent (a guard that warns on any
   unrecognised ``--by`` reddens it), and a RESOLVABLE uuid must stay silent too
   (the warning is about RESOLUTION, not shape). The ``OC_ACTOR`` path is
   untouched — the guard is for an explicit ``--by`` only.

4. GIT TROUBLE NEVER FAILS A STAMP (§34). The ledger is the record; the git tail
   is housekeeping. A stamp in a state dir with no ``.git`` at all must still
   write its row and exit 0.
"""

from __future__ import annotations

import json

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")

W2 = "11111111-2222-3333-4444-555555555555"
W2_PREFIX = "11111111"                      # the unique prefix of the enrolled W2
FULL = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"   # the sandbox's own worker
GHOST = "99999999-8888-7777-6666-555555555555"
FABRICATED = "triage 530c29ec-9ba9-4d3e-9d5f-3b7d1b0d1a1f"
LABEL = "hq/opencrabs-dev-factory"


@pytest.fixture
def roster(ledger_sandbox, run_tool):
    """The sandbox, plus the second worker the derivation ladder needs.

    ``enroll`` is what puts W2 on the roster, and it is asserted on its own —
    a fixture that silently failed to enroll would make every ``derive-by-*``
    leg fall back to the sentinel and still "pass" the sentinel assertions.
    """
    def call(*args, env=None, timeout=120):
        return run_tool([str(TOOL), *args], timeout=timeout, env=env or {})

    res = call("enroll", W2, "tester", "--topic", "42")
    assert res.rc == 0, (
        "[enroll-w2] fixture: enroll %s failed rc=%s\n%s"
        % (W2, res.rc, res.combined[-1200:]))
    ledger_sandbox.call = call
    return ledger_sandbox


def _stamp(sb, what, *, env=None, by=None):
    args = ["stamp", "note", what]
    if by is not None:
        args += ["--by", by]
    return sb.call(*args, env=env)


def _by_of(sb, what, ledger=None):
    """The ``by`` field of the LAST row carrying ``what``."""
    rows = [e for e in L.events(ledger or sb.ledger) if e.get("what") == what]
    assert rows, "fixture: no row with what=%r — the stamp never landed" % (what,)
    return rows[-1].get("by")


# =============================================================================
# §34 — git trouble never fails a stamp
# =============================================================================
def test_a_stamp_survives_a_state_dir_with_no_git(roster):
    """``stamp-survives-no-git``.

    The ledger is the record; the git tail is housekeeping. A state dir with no
    ``.git`` at all is the shape a fresh fixture or a restored backup has, and a
    stamp there must still write its row and exit 0 — a housekeeping failure
    that eats the record is the tail outranking the thing it serves.
    """
    import shutil

    shutil.rmtree(roster.state / ".git", ignore_errors=True)
    assert not (roster.state / ".git").exists(), "fixture: .git still present"

    res = _stamp(roster, "no-git")

    assert res.rc == 0, (
        "[stamp-survives-no-git] rc=%s, want 0 — git trouble must never fail a "
        "stamp:\n%s" % (res.rc, res.combined[-1200:]))
    assert _by_of(roster, "no-git"), (
        "[stamp-survives-no-git] the row did not land — rc 0 with no record is "
        "worse than a refusal")


# =============================================================================
# §19 — an anonymous row is refused, and the refusal is complete
# =============================================================================
def test_an_anonymous_stamp_is_refused_and_names_all_three_remedies(roster):
    """``anon-refused-rc`` + ``-names-by`` + ``-names-actor`` +
    ``-names-override`` + ``-wrote-nothing``.

    #19: warn-and-write made the defect the default — every caller that forgot
    an actor still produced a row, and the row read as legitimate. The refusal
    must name ALL THREE remedies; naming one leaves the operator guessing at the
    other two, and ``--allow-unattributed`` is the only one that unblocks a
    caller who genuinely has no actor.

    And it must WRITE NOTHING. A refusal that still stamps is a warn in disguise,
    and the ``wrote-nothing`` leg is the only one that can tell the difference.
    """
    anon = {"OC_ACTOR": "", "OPENCRABS_SESSION_ID": ""}

    res = _stamp(roster, "anon-stamp", env=anon)

    assert res.rc == 2, (
        "[anon-refused-rc] rc=%s, want 2 — an anonymous row must be refused, "
        "not warned about:\n%s" % (res.rc, res.combined[-1200:]))
    for needle, name in (("--by", "anon-refused-names-by"),
                         ("OC_ACTOR", "anon-refused-names-actor"),
                         ("--allow-unattributed", "anon-refused-names-override")):
        assert needle in res.combined, (
            "[%s] the refusal does not name %r — an operator given one remedy "
            "out of three cannot tell which one they are missing:\n%s"
            % (name, needle, res.combined[-1200:]))

    wrote = [e for e in L.events(roster.ledger) if e.get("what") == "anon-stamp"]
    assert wrote == [], (
        "[anon-refused-wrote-nothing] the refusal still wrote %d row(s) — a "
        "refusal that stamps is a warn wearing a refusal's exit code" % len(wrote))


def test_the_unattributed_hatch_lands_a_loudly_marked_row(roster):
    """``anon-override-rc`` + ``derive-by-no-actor-loud``.

    The hatch must WORK (a refusal with no declared window is a wall), and the
    row it produces must be MARKED — ``by`` containing ``unattributed`` — so a
    later audit can find every row nobody signed. An override that produced a
    row indistinguishable from an attributed one would defeat the refusal it
    bypasses.
    """
    anon = {"OC_ACTOR": "", "OPENCRABS_SESSION_ID": ""}

    # The hatch is a FLAG, not a --by value: a caller with no actor at all still
    # has no uuid to pass, so --by would not be a remedy here.
    res = roster.call("stamp", "note", "anon-stamp", "--allow-unattributed",
                      env=anon)

    assert res.rc == 0, (
        "[anon-override-rc] rc=%s, want 0 — --allow-unattributed is the declared "
        "window past the refusal:\n%s" % (res.rc, res.combined[-1200:]))
    by = _by_of(roster, "anon-stamp")
    assert "unattributed" in (by or ""), (
        "[derive-by-no-actor-loud] by=%r does not carry 'unattributed' — an "
        "override row indistinguishable from an attributed one defeats the "
        "refusal it bypasses" % (by,))


# =============================================================================
# §35-40 — the derivation ladder
# =============================================================================
def test_a_session_id_resolves_through_the_roster(roster):
    """``derive-by-session-id-rc`` + ``-label``.

    ``OPENCRABS_SESSION_ID`` carrying a ROSTERED uuid must render the roster's
    ``role + full uuid``. This is the live path: the lane exports its session id
    and expects the ledger to know whose it is.
    """
    res = _stamp(roster, "session-id-stamp",
                 env={"OC_ACTOR": "", "OPENCRABS_SESSION_ID": W2})

    assert res.rc == 0, (
        "[derive-by-session-id-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-1200:]))
    assert _by_of(roster, "session-id-stamp") == "tester " + W2, (
        "[derive-by-session-id-label] by=%r, want 'tester %s' — the roster's role "
        "and FULL uuid, not the fragment that was passed in"
        % (_by_of(roster, "session-id-stamp"), W2))


def test_a_rostered_uuid_resolves_and_an_unrostered_one_keeps_the_sentinel(roster):
    """``derive-by-roster-rc`` + ``-label`` + ``derive-by-unrostered``.

    The two arms are a PAIR: one proves resolution works, the other proves an
    unknown actor is not invented. A ladder that resolved everything would pass
    the first alone and attribute every ghost to whoever was nearest.
    """
    res = _stamp(roster, "worker-stamp", env={"OC_ACTOR": W2})
    assert res.rc == 0, (
        "[derive-by-roster-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-1200:]))
    assert _by_of(roster, "worker-stamp") == "tester " + W2, (
        "[derive-by-roster-label] by=%r, want 'tester %s'"
        % (_by_of(roster, "worker-stamp"), W2))

    res = _stamp(roster, "ghost-stamp", env={"OC_ACTOR": GHOST})
    by = _by_of(roster, "ghost-stamp")
    assert (by or "").startswith("unrostered-actor"), (
        "[derive-by-unrostered] by=%r does not start with 'unrostered-actor' — "
        "an unknown actor must keep the honest sentinel, never be invented" % (by,))


def test_a_uuid_fragment_resolves_against_the_roster(roster):
    """``derive-by-prefix-rc`` + ``-resolves`` + ``-not-sentinel``.

    M2-3: the lookup was an EXACT compare, so 8 live rows carry a bare 8-char
    prefix whose full uuid IS rostered — an unresolvable lookup, not an
    unrostered lane. A unique prefix must resolve.
    """
    res = _stamp(roster, "prefix-stamp", env={"OC_ACTOR": W2_PREFIX})

    assert res.rc == 0, (
        "[derive-by-prefix-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-1200:]))
    by = _by_of(roster, "prefix-stamp")
    assert by == "tester " + W2, (
        "[derive-by-prefix-resolves] by=%r, want 'tester %s' — a unique prefix "
        "must resolve to the full rostered identity" % (by, W2))
    assert not (by or "").startswith("unrostered-actor"), (
        "[derive-by-prefix-not-sentinel] a resolvable prefix took the sentinel")


def test_a_fragment_matching_nothing_keeps_the_sentinel_and_names_the_remedy(roster):
    """``derive-by-nomatch-rc`` + ``-sentinel`` + ``-names-enroll``.

    The sentinel is honest — never an invented identity — but a silent sentinel
    is an invisible defect: the row looks attributed-ish and nothing tells the
    operator how to fix it. The remedy is ``enroll``.
    """
    res = _stamp(roster, "nomatch-stamp", env={"OC_ACTOR": "ffffffff"})

    assert res.rc == 0, (
        "[derive-by-nomatch-rc] rc=%s, want 0 — an unresolvable actor is a "
        "stamp that lands with a sentinel, not a failure:\n%s"
        % (res.rc, res.combined[-1200:]))
    by = _by_of(roster, "nomatch-stamp")
    assert (by or "").startswith("unrostered-actor"), (
        "[derive-by-nomatch-sentinel] by=%r — a fragment matching nothing must "
        "keep the sentinel" % (by,))
    assert "oc-ledger enroll" in res.combined, (
        "[derive-by-nomatch-names-enroll] the sentinel path does not name the "
        "remedy, so the operator cannot fix the attribution:\n%s"
        % (res.combined[-1200:],))


def test_the_sentinel_is_idempotent_never_prefixed_twice(roster):
    """``derive-by-sentinel-idem-rc`` + ``-verbatim`` + ``-warns``.

    M2-23: an actor already in sentinel form is echoed VERBATIM. Feeding a prior
    row's ``by`` back is the natural caller pattern — the roster TSV's first two
    columns are exactly this shape — and a second prefix would produce
    ``unrostered-actor unrostered-actor …``, growing without bound and destroying
    the identity it was meant to preserve.

    The warning leg is the other half: idempotence must be VISIBLE, or the next
    caller cannot tell their input was already a sentinel.
    """
    res = _stamp(roster, "sentinel-idem-stamp",
                 env={"OC_ACTOR": "unrostered-actor 2fae1230"})

    assert res.rc == 0, (
        "[derive-by-sentinel-idem-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-1200:]))
    assert _by_of(roster, "sentinel-idem-stamp") == "unrostered-actor 2fae1230", (
        "[derive-by-sentinel-idem-verbatim] by=%r, want the input echoed "
        "verbatim — a second prefix corrupts the identity it preserves"
        % (_by_of(roster, "sentinel-idem-stamp"),))
    assert "already carries" in res.combined, (
        "[derive-by-sentinel-idem-warns] the idempotent path is silent, so the "
        "caller cannot tell their input was already a sentinel:\n%s"
        % (res.combined[-1200:],))


def test_a_composed_role_uuid_form_is_consumable(roster):
    """``derive-by-composed-rc`` + ``-canonical`` + ``-not-sentinel`` +
    ``-label-sentinel``.

    M2-24: the composed ``<role> <uuid>`` form ``derive_by`` EMITS must be
    CONSUMABLE — feeding a prior row's ``by`` back in is the natural caller
    pattern. A format the tool writes but cannot read is a round-trip that only
    works in one direction.

    The expected value is DERIVED from the fixture roster, never hardcoded: a
    hardcoded role would silently pin a value the roster owns. And a two-word
    LABEL whose tail is not a uuid must still take the sentinel — the composed
    parse must not accept any two words.
    """
    expected = None
    for w in json.loads(roster.ledger.read_text())["workers"]:
        if w.get("uuid") == FULL:
            expected = "%s %s" % (w.get("role"), FULL)
    assert expected, "fixture: %s is not on the roster" % FULL

    res = _stamp(roster, "composed-stamp", env={"OC_ACTOR": "tester aaaaaaaa"})
    assert res.rc == 0, (
        "[derive-by-composed-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-1200:]))
    by = _by_of(roster, "composed-stamp")
    assert by == expected, (
        "[derive-by-composed-canonical] by=%r, want %r — the composed form must "
        "canonicalise to the roster's role and FULL uuid" % (by, expected))
    assert not (by or "").startswith("unrostered-actor"), (
        "[derive-by-composed-not-sentinel] a valid composed form took the sentinel")

    _stamp(roster, "composed-label-stamp", env={"OC_ACTOR": "some lane label"})
    by = _by_of(roster, "composed-label-stamp")
    assert (by or "").startswith("unrostered-actor"), (
        "[derive-by-composed-label-sentinel] by=%r — a two-word LABEL whose tail "
        "is not a uuid must not be parsed as a composed identity" % (by,))


def test_a_meaningful_label_is_written_verbatim(roster):
    """``stamp-label-rc`` + ``-verbatim``.

    ``--by`` is written VERBATIM for a label. HQ stamps
    ``hq/opencrabs-dev-factory``; refusing or rewriting the label form would
    break that outright, and a label is a legitimate identity — it is the uuid
    shape that is ambiguous, not the words.
    """
    res = _stamp(roster, "label-stamp", by=LABEL)

    assert res.rc == 0, (
        "[stamp-label-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-1200:]))
    assert _by_of(roster, "label-stamp") == LABEL, (
        "[stamp-label-verbatim] by=%r, want %r verbatim"
        % (_by_of(roster, "label-stamp"), LABEL))


# =============================================================================
# #320 — a uuid-SHAPED --by that resolves nowhere WARNs, never refuses
# =============================================================================
def test_a_fabricated_uuid_by_warns_names_the_remedy_and_still_stamps(roster):
    """``by-uuid-shaped-rc`` + ``-warns`` + ``-names-remedy`` +
    ``-still-stamps-verbatim``.

    #320: ``--by`` bypassed ``derive_by`` and wrote verbatim, so a hand-assembled
    uuid (remembered prefix + invented tail) landed as a phantom actor
    indistinguishable from a real one (row n=10499).

    The fix is a WARNING, not a refusal, and the reason is measured: 64 of 86
    sentinel rows belong to uuids rostered TODAY, stamped inside the pre-enroll
    window. Refusing on shape would have rejected legitimate history.

    All four legs matter: the rc proves it does not refuse, the warning proves
    the guard fires, the remedy proves it is actionable, and the verbatim leg
    proves the guard did not silently rewrite the identity it warned about.
    """
    res = _stamp(roster, "by-fabricated-stamp", by=FABRICATED)

    assert res.rc == 0, (
        "[by-uuid-shaped-rc] rc=%s, want 0 — the guard WARNS; a refusal would "
        "reject legitimate pre-enroll history:\n%s"
        % (res.rc, res.combined[-1200:]))
    assert "UUID-SHAPED" in res.combined, (
        "[by-uuid-shaped-warns] a fabricated uuid-shaped --by stamped with no "
        "warning — the phantom-actor defect, silently:\n%s"
        % (res.combined[-1200:],))
    assert "roster --live" in res.combined, (
        "[by-uuid-shaped-names-remedy] the warning does not say how to get a "
        "real uuid:\n%s" % (res.combined[-1200:],))
    assert _by_of(roster, "by-fabricated-stamp") == FABRICATED, (
        "[by-uuid-shaped-still-stamps-verbatim] by=%r, want %r verbatim — the "
        "guard must not rewrite the identity it warned about"
        % (_by_of(roster, "by-fabricated-stamp"), FABRICATED))


def test_the_uuid_warning_stays_silent_for_a_label_a_real_uuid_and_the_actor_path(
        roster):
    """``by-label-no-warn`` + ``by-real-uuid-rc`` + ``-no-warn`` +
    ``by-actor-path-rc`` + ``-no-warn``.

    THREE negative controls, and each is satisfiable by a different broken
    implementation:

    * a LABEL must stay silent — a guard that warns on any unrecognised ``--by``
      reddens this, and it would warn on every HQ row;
    * a RESOLVABLE uuid must stay silent — the warning is about RESOLUTION, not
      shape, so a shape-only guard reddens this;
    * the ``OC_ACTOR`` path must stay silent — the guard is for an explicit
      ``--by`` only, and a guard that also fired here would warn on every
      ordinary stamp on the box.
    """
    res = _stamp(roster, "by-label-silent-stamp", by=LABEL)
    assert "UUID-SHAPED" not in res.combined, (
        "[by-label-no-warn] a LABEL --by raised the uuid warning — that would "
        "warn on every HQ row:\n%s" % (res.combined[-1200:],))

    res = _stamp(roster, "by-real-uuid-stamp", by="tester " + FULL)
    assert res.rc == 0, (
        "[by-real-uuid-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-1200:]))
    assert "UUID-SHAPED" not in res.combined, (
        "[by-real-uuid-no-warn] a RESOLVABLE uuid raised the warning — the guard "
        "is about resolution, not shape:\n%s" % (res.combined[-1200:],))

    res = _stamp(roster, "by-actor-path-stamp", env={"OC_ACTOR": "tester aaaaaaaa"})
    assert res.rc == 0, (
        "[by-actor-path-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-1200:]))
    assert "UUID-SHAPED" not in res.combined, (
        "[by-actor-path-no-warn] the OC_ACTOR path raised the --by warning — the "
        "guard must fire for an explicit --by only, or every ordinary stamp on "
        "the box warns:\n%s" % (res.combined[-1200:],))


# =============================================================================
# an AMBIGUOUS prefix must not resolve
# =============================================================================
def test_an_ambiguous_prefix_keeps_the_sentinel_while_an_exact_uuid_resolves(
        roster, tmp_path):
    """``derive-by-ambiguous-rc`` + ``-sentinel`` + ``-amb-exact-resolves``.

    A wrong pick is worse than an honest sentinel: it silently attributes one
    lane's work to a DIFFERENT lane, and nothing downstream can tell. So a prefix
    matching two roster rows must NOT resolve.

    The exact-uuid leg is the control — it proves the fixture's ambiguity is real
    and that resolution still works on the same file, rather than the sentinel
    coming from a broken fixture.

    Built on an ISOLATED ledger: the shared fixture roster is pinned by the
    roster-count assertions elsewhere, and two extra workers here would redden
    them for a reason unrelated to this claim.
    """
    amb = tmp_path / "amb-ledger.json"
    amb.write_text(json.dumps({
        "current_skill_version": "0.4.1",
        "meta": {"skill_version": "0.4.1", "current_skill_version": "0.4.1"},
        "updated_at": "2026-01-01T00:00:00Z",
        "workers": [
            {"uuid": "77777777-aaaa-1111-1111-111111111111", "role": "editor",
             "topic_id": 1, "feature": "-", "confirmed": True,
             "last_acked": None, "notes": [], "events": []},
            {"uuid": "77777777-bbbb-2222-2222-222222222222", "role": "editor",
             "topic_id": 2, "feature": "-", "confirmed": True,
             "last_acked": None, "notes": [], "events": []},
        ],
        "events": [],
    }), encoding="utf-8")

    res = roster.call("stamp", "note", "amb-stamp",
                      env={"OC_LEDGER": str(amb), "OC_ACTOR": "77777777"})
    assert res.rc == 0, (
        "[derive-by-ambiguous-rc] rc=%s, want 0 — an ambiguous prefix is a "
        "sentinel, not a failure:\n%s" % (res.rc, res.combined[-1200:]))
    by = _by_of(roster, "amb-stamp", ledger=amb)
    assert (by or "").startswith("unrostered-actor"), (
        "[derive-by-ambiguous-sentinel] by=%r — an ambiguous prefix RESOLVED, so "
        "one lane's work is attributed to another and nothing can tell" % (by,))

    exact = "77777777-aaaa-1111-1111-111111111111"
    res = roster.call("stamp", "note", "amb-exact-stamp",
                      env={"OC_LEDGER": str(amb), "OC_ACTOR": exact})
    assert res.rc == 0, (
        "[derive-by-amb-exact-resolves] fixture: the exact-uuid stamp failed "
        "rc=%s\n%s" % (res.rc, res.combined[-1200:]))
    assert _by_of(roster, "amb-exact-stamp", ledger=amb) == "editor " + exact, (
        "[derive-by-amb-exact-resolves] by=%r, want 'editor %s' — an EXACT uuid "
        "must still resolve on the same file, or the sentinel above came from a "
        "broken fixture" % (_by_of(roster, "amb-exact-stamp", ledger=amb), exact))


# =============================================================================
# DELIBERATELY NOT PORTED
# =============================================================================
# Nothing in this range is unported. The three source-grep "single source" arms
# that sit immediately after this block (state-tracked-single-source,
# state-sweep-fn-single-source, state-tracked-audit-single-source) belong to
# test_ledger_structural.py, which ports them as read-only source assertions.
