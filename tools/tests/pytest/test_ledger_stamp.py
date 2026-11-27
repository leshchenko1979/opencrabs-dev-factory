"""Ported: ``oc-ledger`` selftest §"stamp" + §"fixture" — the WRITE path.

Source: ``tools/state/oc-ledger:2805-2911`` (selftest lines 35-141), 30 of the
475 ``chk`` calls. Every ``chk`` name appears verbatim in the assertion message
of the leg that replaces it, so the mapping table in the report is mechanical.

WHAT THIS MODULE PROTECTS
    ``stamp`` and ``fixture`` are the ONLY two ways an event row enters the
    ledger — a one-writer census forbids ``.events +=`` anywhere else. So the
    invariants here are not "the CLI parses arguments"; they are:

    * ``n`` is a dense, monotone ordinal. A gap or a repeat makes every consumer
      that trusts ``n`` (claim scans, ``since``-style tails, the HQ digest) read
      a row that cannot exist. ``n-continuity`` pins the base case: three stamps
      must land 1, 2, 3.
    * a row carries ALL five fields. A row missing ``by`` is unattributable; one
      missing ``t`` cannot be ordered. ``event-fields`` uses ``has()``, not a
      truthiness test, because ``last_acked: null`` is legitimate but an absent
      ``by`` is not.
    * a REFUSAL writes nothing. That is why the refusal arms assert rc only:
      the rc is the whole contract, and ``fixture-refusals-wrote-nothing``
      counts the file to prove the four refused invocations left no trace.
    * text that reaches the ledger must not have been through a shell (#341).
      ``--what-file`` / ``--what-stdin`` exist because a command-line argument is
      expanded by the CALLER's shell before the tool runs, so backticks and
      ``$(...)`` execute and an empty substitution leaves no trace in the stored
      row. The read-back self-verify cannot catch it BY CONSTRUCTION: it compares
      the already-expanded value against the already-expanded copy. Hence the
      payload here carries a literal backtick and a literal ``$HOME``, and the
      legs compare CONTENT — a length assertion would pass on a wrong-but-
      same-length string.

DELIBERATELY NOT PORTED
    * ``stamp-success-line-*`` are ported, but the two ``case`` arms in the shell
      that read ``$T/wf.out`` are folded into the legs that produce that output
      rather than kept as separate greps — same assertion, one process.
    * Nothing here drives ``--selftest`` and nothing sleeps, so no leg is
      ``slow``: each is one or two tool invocations against a throwaway ledger
      in this worker's scratch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")

# The refusal arms, as ``(argv, want_rc, why)``. Kept as one parametrize because
# in the shell they are four consecutive lines (2808-2811) whose whole content
# is the rc: a separate function per arm would add prose without adding a check.
REFUSALS = [
    ("unknown-kind", ["stamp", "bogus-kind", "x"], 2,
     "a kind outside KINDS is a usage error, never a row"),
    ("empty-what", ["stamp", "note", ""], 2,
     "an empty payload writes a row nothing can be attributed to"),
    ("skill-bump-refused", ["stamp", "skill-bump", "x"], 2,
     "skill-bump is sync-only, so a direct stamp would bypass the "
     "receipt/CHANGELOG gates"),
    ("stamp-what-novalue", ["stamp", "note", "--what"], 2,
     "--what with no value is a usage error, not an empty row"),
    ("stamp-unknown-flag", ["stamp", "note", "--bogus", "x"], 2,
     "an unrecognised flag is refused, never silently ignored into a "
     "positional"),
]


# =============================================================================
# the ordinal contract — stamp#1, n-continuity, event-fields
# =============================================================================
def test_three_stamps_land_a_dense_ordinal_and_a_complete_row(
        ledger_sandbox, run_tool):
    """``stamp#1`` + ``n-continuity`` + ``event-fields``.

    ONE test, because the sequence IS the fixture: ``n-continuity`` is only a
    claim about numbering if the three stamps above it actually ran, and
    splitting them would recreate the shell's shared mutable state across
    tests — the thing xdist punishes.
    """
    ledger = Path(ledger_sandbox.ledger)

    res = run_tool([str(TOOL), "stamp", "note", "one"], timeout=120)
    assert res.rc == 0, \
        "[stamp#1] the first stamp is rc=%s, want 0\n%s" % (
            res.rc, res.combined[-800:])

    for kind, what in (("ruling", "two"), ("incident", "three")):
        r = run_tool([str(TOOL), "stamp", kind, what], timeout=120)
        assert r.rc == 0, \
            "[n-continuity] the fixture stamp %r %r is rc=%s, want 0\n%s" % (
                kind, what, r.rc, r.combined[-800:])

    assert L.max_n(ledger) == 3, \
        ("[n-continuity] max n is %r after three stamps, want 3 — a gap or a "
         "repeat makes the row unreadable to every consumer that trusts n "
         "(ordinals in file order: %r)" % (L.max_n(ledger), L.ns(ledger)))
    assert sorted(L.ns(ledger)) == [1, 2, 3], \
        ("[n-continuity] the ordinals are %r, want a DENSE 1,2,3 — 'max is 3' "
         "alone would pass on [1,1,3]" % (L.ns(ledger),))

    row = L.last_event(ledger)
    assert L.has_fields(row, ("n", "t", "by", "kind", "what")), \
        ("[event-fields] the last row is missing a required field: has %r, "
         "want all of n/t/by/kind/what (row=%r)"
         % (sorted(row or {}), row))
    # has() above is the shell's assertion; these two say WHY the field matters,
    # and are additions to the ported set rather than replacements for it.
    assert row["by"], \
        ("[event-fields] the row's actor is empty (%r) — an unattributable row "
         "is what #19 refuses to write" % (row.get("by"),))
    assert row["kind"] == "incident" and row["what"] == "three", \
        ("[event-fields] the last row is %r/%r, want incident/three — the "
         "ordinal and the payload must belong to the SAME row"
         % (row.get("kind"), row.get("what")))


@pytest.mark.parametrize("name,argv,want_rc,why", REFUSALS,
                         ids=[r[0] for r in REFUSALS])
def test_usage_and_kind_refusals(ledger_sandbox, run_tool, name, argv, want_rc,
                                 why):
    """The five rc-2 arms from oc-ledger:2808-2811."""
    res = run_tool([str(TOOL)] + argv, timeout=120)
    assert res.rc == want_rc, \
        "[%s] rc=%s, want %s — %s\n%s" % (
            name, res.rc, want_rc, why, res.combined[-600:])


def test_a_refused_stamp_writes_no_row(ledger_sandbox, run_tool):
    """The refusal contract's OTHER half: rc 2 must leave the log untouched.

    Without this, an implementation that wrote the row and then exited 2 would
    satisfy every arm above. The shell does not assert it here (it relies on
    later ordinals), so this leg is an addition — and it is the one that makes
    the parametrized arms above mean something.
    """
    ledger = Path(ledger_sandbox.ledger)
    before = len(L.events(ledger))

    for name, argv, want_rc, _why in REFUSALS:
        res = run_tool([str(TOOL)] + argv, timeout=120)
        assert res.rc == want_rc, \
            "precondition: [%s] %r is rc=%s, want %s" % (
                name, argv, res.rc, want_rc)

    assert len(L.events(ledger)) == before, \
        ("a refused stamp wrote a row anyway: %d events before, %d after "
         "(every refusal must be a no-op on the record, not just on the rc)"
         % (before, len(L.events(ledger))))


# =============================================================================
# the kind vocabulary — claim (v1.1 marker) and proposal (Duty-4)
# =============================================================================
def test_claim_kind_accepts_a_v1_1_marker(ledger_sandbox, run_tool):
    """``stamp-claim-v1.1``: a claim row carrying a version marker is accepted.

    The v1.1 marker is prose inside ``what``; a kind filter that rejected it
    would close the channel the fleet writes claims through.
    """
    ledger = Path(ledger_sandbox.ledger)
    res = run_tool([str(TOOL), "stamp", "claim", "CLAIM #1234 — v1.1 kind"],
                   timeout=120)
    assert res.rc == 0, \
        "[stamp-claim-v1.1] rc=%s, want 0 — a claim with a version marker in " \
        "its text is an ordinary claim\n%s" % (res.rc, res.combined[-800:])

    row = L.last_where(ledger, kind="claim")
    assert row is not None, \
        "[stamp-claim-v1.1] rc 0 but no claim row landed in the ledger"
    assert row["what"] == "CLAIM #1234 — v1.1 kind", \
        ("[stamp-claim-v1.1] the stored text is %r, want it verbatim — the "
         "marker is part of the payload, not a field to be parsed away"
         % (row.get("what"),))


def test_proposal_kind_is_accepted(ledger_sandbox, run_tool):
    """``stamp-proposal`` + ``stamp-proposal-kind`` (Duty-4, v0.4.152 A1).

    The law mandates ``stamp proposal`` in four places, but the kind was absent
    from KINDS, so the verb died rc 2 and the channel had NEVER accepted a row
    (0 of 3558 events, measured 2026-09-12). A law that names a verb the tool
    refuses is a dead channel, not a lane error — which is why this is asserted
    by rc AND by reading the kind back.
    """
    ledger = Path(ledger_sandbox.ledger)
    res = run_tool([str(TOOL), "stamp", "proposal", "Duty-4 proposal (fixture)"],
                   timeout=120)
    assert res.rc == 0, \
        ("[stamp-proposal] rc=%s, want 0 — Duty-4 mandates this verb in four "
         "documents; a refusal makes it a dead channel\n%s"
         % (res.rc, res.combined[-800:]))

    assert L.field(ledger, "kind", kind="proposal") == "proposal", \
        ("[stamp-proposal-kind] the last proposal row's kind is %r, want "
         "'proposal' — rc 0 with a mislabelled row would pass a rc-only leg"
         % (L.field(ledger, "kind", kind="proposal"),))


# =============================================================================
# the --what flag form and its glitch guards
# =============================================================================
def test_the_what_flag_carries_the_payload(ledger_sandbox, run_tool):
    """``stamp-what-flag`` + ``stamp-what-value``.

    Duty-4 2026-08-31 (n=1361/n=1372 class): a stamp whose text arrived as a
    FLAG was stored with the wrong payload. rc 0 alone would not catch it, so
    the value is read back.
    """
    ledger = Path(ledger_sandbox.ledger)
    res = run_tool([str(TOOL), "stamp", "note", "--what", "flag-form text"],
                   timeout=120)
    assert res.rc == 0, \
        "[stamp-what-flag] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:])

    assert L.field(ledger, "what", kind="note") == "flag-form text", \
        ("[stamp-what-value] the stored text is %r, want 'flag-form text' — "
         "the --what flag must carry the payload, not the flag name"
         % (L.field(ledger, "what", kind="note"),))


# =============================================================================
# a missing / corrupt ledger is rc 3, never a new file and never a crash
# =============================================================================
def test_a_missing_ledger_is_rc3(ledger_sandbox, run_tool):
    """``ledger-missing``: pointing at a nonexistent ledger is rc 3.

    3, not 2: the usage was well-formed, the STORE is what is absent. A tool
    that CREATED the file here would silently start a second, empty ledger and
    every later reader would see a fleet with no history.
    """
    missing = Path(ledger_sandbox) / "nope.json"
    res = run_tool([str(TOOL), "stamp", "note", "x"], timeout=120,
                   env={"OC_LEDGER": str(missing)})
    assert res.rc == 3, \
        "[ledger-missing] rc=%s, want 3\n%s" % (res.rc, res.combined[-800:])
    assert not missing.exists(), \
        ("[ledger-missing] the tool CREATED %s — a stamp against a missing "
         "ledger must not invent an empty one" % (missing,))


def test_a_corrupt_ledger_is_rc3(ledger_sandbox, run_tool):
    """``ledger-corrupt``: an unparseable ledger is rc 3 and is left alone.

    Left alone matters as much as the rc: rewriting a corrupt file would destroy
    the evidence a recovery needs.
    """
    bad = Path(ledger_sandbox) / "bad.json"
    bad.write_text("{broken", encoding="utf-8")

    res = run_tool([str(TOOL), "stamp", "note", "x"], timeout=120,
                   env={"OC_LEDGER": str(bad)})
    assert res.rc == 3, \
        "[ledger-corrupt] rc=%s, want 3\n%s" % (res.rc, res.combined[-800:])
    assert bad.read_text(encoding="utf-8") == "{broken", \
        ("[ledger-corrupt] the tool REWROTE the corrupt ledger to %r — a "
         "recovery needs the original bytes"
         % (bad.read_text(encoding="utf-8")[:120],))


# =============================================================================
# #341: shell-free text input
# =============================================================================
# A payload that a shell WOULD mangle: backticks are command substitution and
# $HOME is a variable. Reaching the ledger verbatim is the whole point of the
# --what-file / --what-stdin forms, so this string is the fixture, not decoration.
PAYLOAD_TEXT = ("names the messages table in backticks `messages` and a dollar "
                "`$HOME` too")


def _write_payload(sandbox, name="payload.txt") -> tuple[Path, str]:
    """Write the payload and return ``(path, what the ledger must store)``.

    The stored form is the text with trailing newlines REMOVED: the tool strips
    them (measured — a 74-byte file stores 73 bytes), which is also what the
    shell's ``WANT_TEXT="$(cat …)"`` produces. Comparing against the raw file
    bytes instead would fail on a correct tool.
    """
    p = Path(sandbox) / name
    p.write_text(PAYLOAD_TEXT + "\n", encoding="utf-8")
    return p, PAYLOAD_TEXT


def test_what_file_roundtrips_shell_hostile_text(ledger_sandbox, run_tool):
    """``stamp-what-file-rc`` + ``stamp-what-file-roundtrip`` +
    ``stamp-success-line-len`` + ``stamp-success-line-hash8``.

    The success line must SURFACE the stored bytes (len + hash8) so a caller
    whose shell ate a word can SEE the bite — the read-back cannot tell them,
    because it compares the already-expanded value against itself.
    """
    ledger = Path(ledger_sandbox.ledger)
    payload, want = _write_payload(ledger_sandbox)

    res = run_tool([str(TOOL), "stamp", "note", "--what-file", str(payload)],
                   timeout=120)
    assert res.rc == 0, \
        "[stamp-what-file-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:])

    stored = L.field(ledger, "what", kind="note")
    assert stored == want, \
        ("[stamp-what-file-roundtrip] stored %r, want %r — the text must reach "
         "the ledger byte-for-byte, with the backtick and $HOME intact"
         % (stored, want))

    assert ("len=%d" % L.byte_len(want)) in res.combined, \
        ("[stamp-success-line-len] the success line does not report len=%d, so "
         "a caller whose shell ate a word cannot see it: %r"
         % (L.byte_len(want), res.combined.strip()))

    assert ("hash8=" + L.sha256_8(want)) in res.combined, \
        ("[stamp-success-line-hash8] the success line does not report "
         "hash8=%s: %r" % (L.sha256_8(want), res.combined.strip()))


def test_what_stdin_roundtrips_the_same_text(ledger_sandbox, run_tool):
    """``stamp-what-stdin-rc`` + ``stamp-what-stdin-roundtrip``.

    stdin is the second shell-free path, and it is asserted separately because
    it is a different read: a tool that wired only ``--what-file`` would pass
    the file leg and drop every stdin payload.
    """
    ledger = Path(ledger_sandbox.ledger)
    payload, want = _write_payload(ledger_sandbox)

    # The newline goes IN on purpose: stdin is not command-substituted, so the
    # stripping this asserts is the TOOL's, not the shell's.
    res = run_tool([str(TOOL), "stamp", "note", "--what-stdin"], timeout=120,
                   stdin_data=payload.read_text(encoding="utf-8"))
    assert res.rc == 0, \
        "[stamp-what-stdin-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:])

    stored = L.field(ledger, "what", kind="note")
    assert stored == want, \
        ("[stamp-what-stdin-roundtrip] stored %r, want %r — stdin text must "
         "land verbatim and the trailing newline must be stripped by the tool"
         % (stored, want))


def test_the_surfaced_hash8_is_derived_from_the_stored_bytes(
        ledger_sandbox, run_tool):
    """``stamp-hash8-anti-vacuity``.

    The shell compares two hashes and calls them different. Here the assertion
    is the one that actually discriminates: the hash the tool PRINTED must be
    the hash of what it STORED, and must differ from the hash of a different
    text. A constant (or a hash of the argv, not the payload) reddens both.
    """
    ledger = Path(ledger_sandbox.ledger)
    payload, want = _write_payload(ledger_sandbox)

    res = run_tool([str(TOOL), "stamp", "note", "--what-file", str(payload)],
                   timeout=120)
    assert res.rc == 0, "precondition: --what-file rc=%s" % res.rc

    printed = L.sha256_8(want)
    other = L.sha256_8("x")
    assert printed != other, \
        ("[stamp-hash8-anti-vacuity] two different texts collide on hash8 "
         "(%s) — the surfaced value cannot distinguish a mangled payload"
         % printed)
    assert ("hash8=" + printed) in res.combined, \
        ("[stamp-hash8-anti-vacuity] the surfaced hash8 is not the hash of the "
         "stored bytes: %r" % res.combined.strip())
    assert ("hash8=" + other) not in res.combined, \
        ("[stamp-hash8-anti-vacuity] the surfaced hash8 is the hash of 'x', not "
         "of the payload — it is not derived from what was stored")


def test_exactly_one_text_source_is_allowed(ledger_sandbox, run_tool):
    """``stamp-two-sources-refused``.

    Two sources is ambiguous, and an implementation that silently preferred one
    would store text the caller did not intend while reporting success.
    """
    payload, _want = _write_payload(ledger_sandbox)
    res = run_tool([str(TOOL), "stamp", "note", "--what", "x",
                    "--what-file", str(payload)], timeout=120)
    assert res.rc == 2, \
        ("[stamp-two-sources-refused] rc=%s, want 2 — two text sources must be "
         "refused, not silently resolved\n%s" % (res.rc, res.combined[-600:]))


def test_a_missing_what_file_names_the_tool_s_own_diagnostic(
        ledger_sandbox, run_tool):
    """``stamp-what-file-missing`` + ``stamp-what-file-missing-owned-diagnostic``.

    The second leg is the interesting one. With the tool's ``-r`` guard removed,
    ``cat`` still fails and its message still names the path — so a
    path-substring assertion passes on a tool that never checked anything
    (mutation-checked: M4 stayed GREEN on that weaker form). "not readable" is a
    string ``cat`` cannot produce, so asserting it is what proves the tool owns
    the check.
    """
    missing = Path(ledger_sandbox) / "does-not-exist.txt"
    res = run_tool([str(TOOL), "stamp", "note", "--what-file", str(missing)],
                   timeout=120)
    assert res.rc == 2, \
        "[stamp-what-file-missing] rc=%s, want 2 (usage)\n%s" % (
            res.rc, res.combined[-600:])
    assert "not readable" in res.err, \
        ("[stamp-what-file-missing-owned-diagnostic] stderr does not carry the "
         "tool's own 'not readable' — a path substring alone would also be "
         "produced by `cat` failing, so this is the assertion that proves the "
         "guard exists: %r" % (res.err.strip(),))


# =============================================================================
# the `fixture` verb — chosen ordinal, chosen timestamp
# =============================================================================
def _jsonl_events(path) -> list:
    """Read a JSONL event file (the fixture verb's record, not the ledger)."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


@pytest.fixture
def fixture_store(ledger_sandbox):
    """The shell's ``$FX``: a JSONL record seeded at n=7, plus an empty ledger.

    The seed ordinal is 7 and the fixture asks for 9, so an implementation that
    DERIVED ``n`` lands 8 and reddens both the equality leg and its
    anti-vacuity twin. The forced ``t`` is a date in the PAST on purpose: a verb
    that stamped ``now`` stores today and reddens the verbatim leg.
    """
    fx = Path(ledger_sandbox) / "fixture-jsonl"
    fx.mkdir(parents=True, exist_ok=True)
    (fx / "events.jsonl").write_text(
        '{"n":7,"t":"2026-11-01T00:00:00Z","by":"seed","kind":"note",'
        '"what":"seed row"}\n', encoding="utf-8")
    (fx / "workers.json").write_text('{"workers":[],"meta":{}}\n',
                                     encoding="utf-8")
    return fx


def _fx_run(run_tool, fx, *args, **kw):
    """Invoke ``fixture`` against the seeded record."""
    return run_tool([str(TOOL), "fixture"] + [str(a) for a in args],
                    timeout=120, env={"OC_LEDGER": str(fx / "workers-ledger.json")},
                    **kw)


def test_fixture_forces_the_ordinal_and_the_timestamp(ledger_sandbox, run_tool,
                                                      fixture_store):
    """``fixture-rc`` + ``fixture-forced-n`` + ``fixture-forced-n-not-derived``
    + ``fixture-forced-t-verbatim`` + ``fixture-kind-by-what-verbatim``
    + ``fixture-row-on-the-record``.

    The one-writer census forbids ``.events +=`` outside the tool, so a fixture
    builder that needs a CHOSEN ordinal and a CHOSEN stamp must come through a
    verb. These arms pin the FORCING itself.
    """
    fx = fixture_store
    record = fx / "events.jsonl"

    res = _fx_run(run_tool, fx, "--n", 9, "--t", "2026-09-24T00:00:00Z",
                  "--kind", "note", "--by", "hq", "--what", "forced fixture row")
    assert res.rc == 0, \
        "[fixture-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:])

    rows = _jsonl_events(record)
    last = rows[-1]
    assert last["n"] == 9, \
        "[fixture-forced-n] stored n=%r, want 9" % (last.get("n"),)
    assert last["n"] != 8, \
        ("[fixture-forced-n-not-derived] the ordinal was DERIVED (8) instead of "
         "forced (9) — a fixture that cannot choose its ordinal cannot seed a "
         "chosen history")
    assert last["t"] == "2026-09-24T00:00:00Z", \
        ("[fixture-forced-t-verbatim] stored t=%r, want the forced past date — "
         "a verb that stamped `now` would store today"
         % (last.get("t"),))
    assert (last["kind"], last["by"], last["what"]) == \
        ("note", "hq", "forced fixture row"), \
        ("[fixture-kind-by-what-verbatim] stored %r, want "
         "(note, hq, forced fixture row)" % ((last.get("kind"), last.get("by"),
                                              last.get("what")),))
    assert len(rows) == 2, \
        ("[fixture-row-on-the-record] the record holds %d rows, want 2 (seed + "
         "fixture) — the row must land on the RECORD, not on a derived view"
         % len(rows))


def test_fixture_what_file_carries_shell_hostile_bytes(ledger_sandbox, run_tool,
                                                       fixture_store):
    """``fixture-what-file-rc`` + ``fixture-what-file-verbatim`` (#341 class)."""
    fx = fixture_store
    payload = Path(ledger_sandbox) / "fx-payload.txt"
    payload.write_text("forced `text` with $HOME\n", encoding="utf-8")

    res = _fx_run(run_tool, fx, "--n", 12, "--t", "2026-09-24T00:00:01Z",
                  "--kind", "note", "--by", "hq", "--what-file", payload)
    assert res.rc == 0, \
        "[fixture-what-file-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:])

    stored = _jsonl_events(fx / "events.jsonl")[-1]["what"]
    assert stored == "forced `text` with $HOME", \
        ("[fixture-what-file-verbatim] stored %r, want the payload verbatim — "
         "a command-line --what would have expanded the backticks and $HOME"
         % (stored,))


def test_fixture_claim_carries_the_derived_issues_field(ledger_sandbox, run_tool,
                                                        fixture_store):
    """``fixture-claim-rc`` + ``fixture-claim-issues-field``
    + ``fixture-claim-visible-to-claims``.

    A seeded claim must carry the structured ``issues`` field ``cmd_stamp``
    derives, or it is invisible to the scanner that keys on it — a fixture that
    seeded a claim without it would test a row shape the live writer never
    produces.
    """
    fx = fixture_store
    res = _fx_run(run_tool, fx, "--n", 13, "--t", "2026-09-24T00:00:02Z",
                  "--kind", "claim", "--by", "hq",
                  "--what", "CLAIM #777 — fixture claim")
    assert res.rc == 0, \
        "[fixture-claim-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:])

    last = _jsonl_events(fx / "events.jsonl")[-1]
    assert (last.get("issues") or [None])[0] == 777, \
        ("[fixture-claim-issues-field] the seeded claim's issues[0] is %r, want "
         "777 — without the derived field the row is invisible to the scanner"
         % ((last.get("issues") or [None])[0],))

    seen = run_tool([str(TOOL), "claims", "777"], timeout=120,
                    env={"OC_LEDGER": str(fx / "workers-ledger.json")})
    hits = sum(1 for ln in seen.out.splitlines() if "fixture claim" in ln)
    assert hits == 1, \
        ("[fixture-claim-visible-to-claims] `claims 777` shows the seeded row "
         "%d times, want 1 — the fixture row must be visible to the scanner "
         "that keys on issues[]\n%s" % (hits, seen.combined[-600:]))


def test_fixture_requires_n_and_t_and_writes_nothing_on_refusal(
        ledger_sandbox, run_tool, fixture_store):
    """``fixture-n-required`` + ``fixture-t-required`` + ``fixture-kind-validated``
    + ``fixture-by-required`` + ``fixture-refusals-wrote-nothing``.

    ``--n`` and ``--t`` are REQUIRED — that is the verb's purpose — so their
    absence is rc 2 rather than a silently derived value. And because the verb's
    whole reason to exist is a CHOSEN history, a refusal that still wrote a row
    would corrupt exactly the thing it is for.
    """
    fx = fixture_store
    record = fx / "events.jsonl"

    arms = [
        (("--t", "2026-09-24T00:00:00Z", "--kind", "note", "--by", "hq",
          "--what", "x"), "fixture-n-required"),
        (("--n", 11, "--kind", "note", "--by", "hq", "--what", "x"),
         "fixture-t-required"),
        (("--n", 11, "--t", "2026-09-24T00:00:00Z", "--kind", "bogus",
          "--by", "hq", "--what", "x"), "fixture-kind-validated"),
        (("--n", 11, "--t", "2026-09-24T00:00:00Z", "--kind", "note",
          "--what", "x"), "fixture-by-required"),
    ]
    for argv, name in arms:
        res = _fx_run(run_tool, fx, *argv)
        assert res.rc == 2, \
            "[%s] rc=%s, want 2 (a required flag is missing or a kind is " \
            "invalid — never a silently derived value)\n%s" % (
                name, res.rc, res.combined[-600:])

    assert len(_jsonl_events(record)) == 1, \
        ("[fixture-refusals-wrote-nothing] the record holds %d rows after four "
         "refusals, want 1 (the seed alone) — a refused fixture must not write"
         % len(_jsonl_events(record)))
