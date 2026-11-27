"""Ported: ``oc-ledger`` selftest §149 — ``migrate --to jsonl``.

Source: ``tools/state/oc-ledger:5371-5496`` (selftest lines 2601-2726) — 17
``chk`` calls plus 14 ``ok || bad`` legs. Every assertion message carries the
shell name it replaces.

WHAT THIS MODULE PROTECTS — the migration, and the two defects it exists for

1. THE DESTINATION GUARD. The guard compared ``STATE_DIR()`` against
   ``$STATE_DIR_DEFAULT``, and BOTH read ``$OC_DEV_STATE`` — so with that
   variable set they were equal BY CONSTRUCTION and every scratch dir was
   refused as "the LIVE state dir". The shell arm that used to sit there
   ASSERTED that false positive, which is exactly how the guard stayed green
   while broken: the arm encoded the bug.

   So a genuine live dir is spelled from a RELOCATED ``$HOME`` (``LIVE_STATE_DIR``
   is built from ``$HOME`` and nothing else — that is the fix), and the
   POSITIVE CONTROL is a scratch dir reached through ``OC_DEV_STATE``. Without
   that control the guard could satisfy the refusal leg by refusing everything,
   which is the defect being fixed.

2. THE REFUSAL'S OWN REMEDY MUST EXIST. The refusal printed "Use ``--ledger
   <scratch>/workers-ledger.json``", and ``migrate``'s arg loop did not accept
   ``--ledger`` at all (rc 2, "unknown argument"). The one instruction the
   operator was given could not be followed. This leg runs the printed remedy
   VERBATIM rather than a paraphrase of it.

3. THE THREE SCHEMA GENERATIONS SURVIVE, VERBATIM. The fixture carries modern
   rows, a legacy ``ts``/``type``/``text`` row with no ``n`` and no ``kind``, a
   row with no ``t``, an explicit ``null`` ``n``, and a duplicate ``n``. The
   migration must carry every one unchanged: renumbering a null, deduping a
   duplicate, or normalising a kindless row is DATA LOSS dressed as tidying,
   and the ledger is append-only history whose ordinals are cited by other rows.

4. THE VIEW IS DERIVED, NOT COPIED. ``workers-ledger.json`` after the migration
   must be reconstructible from ``events.jsonl`` + ``workers.json``. A migration
   that leaves the view a copy of the old blob has moved nothing: the next write
   still rewrites O(n), which is the whole reason the record became text.

5. THE POINT OF THE WHOLE CHANGE: a ``stamp`` appends exactly ONE line. Without
   this arm the migration could be correct and the write path still O(n).

FIXTURE NOTE
    ``HOME`` is relocated per call rather than monkeypatched, so a single test
    can point two different homes at the same tool. ``env_guard`` still
    redirects the live fleet vars; the relocated home is an additional layer,
    not a replacement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-ledger")

# Three schema generations in one file: modern, legacy (ts/type/text, no n, no
# kind), no-t, explicit null n, duplicate n, no-kind. Copied verbatim from the
# shell heredoc — it is the specimen the traps were found on.
SEED = {
    "workers": [{"uuid": "14914914-9149-4914-9149-149149149149",
                 "role": "editor", "topic_id": 9}],
    "events": [
        {"n": 1, "t": "2026-01-01T00:00:00Z", "kind": "claim",
         "what": "modern row"},
        {"n": 2, "t": "2026-01-02T00:00:00Z", "kind": "note",
         "what": "modern row two"},
        {"t": "2026-01-03T00:00:00Z", "type": "legacy",
         "text": "legacy: ts+type+text, no n, no kind"},
        {"n": 3, "kind": "note", "what": "no t at all"},
        {"n": None, "t": "2026-01-04T00:00:00Z", "kind": "note",
         "what": "explicit null n"},
        {"n": 1258, "t": "2026-01-05T00:00:00Z", "what": "no kind, duplicate n"},
        {"n": 1258, "t": "2026-01-05T00:00:01Z",
         "what": "no kind, duplicate n again"},
        {"n": 4, "t": "2026-01-06T00:00:00Z", "kind": "note", "what": "tail row"},
    ],
    "meta": {"generation": 3},
}


class Mig:
    """``seed149`` + a ``migrate`` callable with a RELOCATED ``$HOME``."""

    def __init__(self, root: Path, run_tool):
        self.root = root
        self.home = root / "home"
        self.live = self.home / ".opencrabs" / "profiles" / "ops" / "opencrabs-dev"
        self.live.mkdir(parents=True, exist_ok=True)
        self._run_tool = run_tool

    @property
    def live_ledger(self) -> Path:
        return self.live / "workers-ledger.json"

    def seed(self, dest: Path) -> Path:
        """Write the fixture ledger into ``dest/state/workers-ledger.json``."""
        state = Path(dest) / "state"
        state.mkdir(parents=True, exist_ok=True)
        path = state / "workers-ledger.json"
        path.write_text(json.dumps(SEED, indent=1), encoding="utf-8")
        return path

    def seed_live(self) -> Path:
        """Put the fixture ledger in the RELOCATED home's live profile dir."""
        self.live_ledger.write_text(json.dumps(SEED, indent=1), encoding="utf-8")
        return self.live_ledger

    def __call__(self, *args, dev_state: str = "", ledger: Path | None = None):
        env = {"HOME": str(self.home), "OC_DEV_STATE": dev_state}
        if ledger is not None:
            env["OC_LEDGER"] = str(ledger)
        return self._run_tool([str(TOOL), "migrate", *args], timeout=180, env=env)

    def stamp(self, what: str):
        env = {"OC_NO_FLOODGUARD": "1",
               "OC_ACTOR": "14914914-9149-4914-9149-149149149149"}
        return self._run_tool([str(TOOL), "stamp", "note", what], timeout=120,
                              env=env)


@pytest.fixture
def mig(tmp_path, run_tool):
    """Per-TEST root.

    NOT ``scratch``: that is one root per WORKER, shared by every test in it, so
    a second leg re-seeded the same ``a/state`` and the migration correctly
    refused an existing record ("already exists — refusing to clobber a live
    record"). The refusal was right; the fixture was reusing a directory it had
    already migrated. ``tmp_path`` is per test.
    """
    root = Path(tmp_path) / "m149"
    root.mkdir(parents=True, exist_ok=True)
    return Mig(root, run_tool)


def _read_jsonl(path: Path) -> list:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def _dup_groups(rows) -> int:
    counts = {}
    for e in rows:
        n = e.get("n")
        counts[n] = counts.get(n, 0) + 1
    return sum(1 for c in counts.values() if c > 1)


# =============================================================================
# (1)(1b)(1c) — the destination guard, three ways
# =============================================================================
def test_the_live_state_dir_is_refused_and_nothing_is_written(mig):
    """``mig149-refuses-the-live-state-dir`` + ``-live-refusal-wrote-nothing`` +
    ``-live-refusal-names-the-reason``.

    The live dir is spelled from a RELOCATED ``$HOME``, so the guard is
    exercised without ever pointing at the real record. The refusal must be
    rc 2, must write NOTHING, and must SAY why — a bare refusal leaves the
    operator guessing which of several destinations was judged live.
    """
    ledger = mig.seed_live()

    res = mig("--to", "jsonl", ledger=ledger)

    assert res.rc == 2, (
        "[mig149-refuses-the-live-state-dir] rc=%s, want 2 — migrating the live "
        "record in place is the refusal this guard exists for:\n%s"
        % (res.rc, res.combined[-1200:]))
    assert not (mig.live / "events.jsonl").exists(), (
        "[mig149-live-refusal-wrote-nothing] the refusal still wrote "
        "events.jsonl beside the live record")
    assert "refusing to migrate the LIVE state dir" in res.combined, (
        "[mig149-live-refusal-names-the-reason] the refusal does not name the "
        "reason, so the operator cannot tell which destination was judged "
        "live:\n%s" % (res.combined[-1200:],))


def test_a_scratch_dir_is_not_refused_when_OC_DEV_STATE_is_set(mig):
    """``mig149-scratch-not-refused-when-OC_DEV_STATE-set`` +
    ``-scratch-guard-false-positive-wrote-nothing`` +
    ``-scratch-guard-false-positive-diagnostic``.

    THE POSITIVE CONTROL, and the arm that pins #149's defect: the guard
    compared ``STATE_DIR()`` against ``$STATE_DIR_DEFAULT`` while BOTH read
    ``$OC_DEV_STATE``, so with that variable set they were equal by construction
    and every scratch dir was refused as live.

    Without this leg the guard could satisfy the refusal above by refusing
    everything — which is precisely the defect.
    """
    state = mig.root / "scratch" / "state"
    ledger = mig.seed(mig.root / "scratch")

    res = mig("--to", "jsonl", dev_state=str(state), ledger=ledger)

    assert res.rc == 0, (
        "[mig149-scratch-not-refused-when-OC_DEV_STATE-set] rc=%s, want 0 — a "
        "scratch destination must not be refused just because OC_DEV_STATE is "
        "set; that equality-by-construction is the #149 defect:\n%s"
        % (res.rc, res.combined[-1500:]))
    out = state / "events.jsonl"
    assert out.exists() and out.stat().st_size > 0, (
        "[mig149-scratch-guard-false-positive-wrote-nothing] the scratch "
        "migration reported success and wrote no record")
    assert "LIVE state dir" not in res.combined, (
        "[mig149-scratch-guard-false-positive-diagnostic] the false-positive "
        "diagnostic fired on a scratch dir:\n%s" % (res.combined[-1500:],))


def test_the_live_flag_still_permits_the_live_dir(mig):
    """``mig149-live-flag-permits-the-live-dir`` + ``-live-flag-wrote-the-record``.

    The bypass must be LIVE, or the guard is a wall with no declared window —
    and an operator with a genuine need to migrate the live record has no path
    at all, which is how a guard gets deleted by the next person.
    """
    ledger = mig.seed_live()

    res = mig("--to", "jsonl", "--live", ledger=ledger)

    assert res.rc == 0, (
        "[mig149-live-flag-permits-the-live-dir] rc=%s, want 0 — --live is the "
        "declared window through the guard:\n%s" % (res.rc, res.combined[-1200:]))
    out = mig.live / "events.jsonl"
    assert out.exists() and out.stat().st_size > 0, (
        "[mig149-live-flag-wrote-the-record] --live was accepted and wrote no "
        "record")


# =============================================================================
# (1d) — the printed remedy must be a real flag
# =============================================================================
def test_the_printed_remedy_is_a_flag_that_works_verbatim(mig):
    """``mig149-printed-remedy-is-a-real-flag`` +
    ``-printed-remedy-migrated-the-copy`` + ``-ledger-flag-without-value``.

    #149 DEFECT 2: the refusal printed "Use ``--ledger <scratch>/workers-ledger.json``"
    while ``migrate``'s arg loop accepted no ``--ledger`` at all. The one
    instruction the operator was given could not be followed.

    Run VERBATIM — ``--ledger <path>`` — because a paraphrase would keep passing
    after the flag's real spelling drifted. And the flag must still reject a
    missing value: a remedy that silently migrates nothing when its argument is
    absent is the same dead end one step later.
    """
    ledger = mig.seed(mig.root / "remedy")

    res = mig("--to", "jsonl", "--ledger", ledger)
    assert res.rc == 0, (
        "[mig149-printed-remedy-is-a-real-flag] rc=%s, want 0 — the refusal's "
        "own printed remedy must be runnable:\n%s" % (res.rc, res.combined[-1200:]))
    out = mig.root / "remedy" / "state" / "events.jsonl"
    assert out.exists() and out.stat().st_size > 0, (
        "[mig149-printed-remedy-migrated-the-copy] the printed remedy was "
        "accepted and migrated nothing")

    bare = mig("--to", "jsonl", "--ledger")
    assert bare.rc == 2, (
        "[mig149-ledger-flag-without-value] rc=%s, want 2 — a flag with no "
        "value must be a usage error, not a silent no-op:\n%s"
        % (bare.rc, bare.combined[-900:]))


# =============================================================================
# (2)(3) — a scratch migration, and the three generations carried verbatim
# =============================================================================
def test_a_scratch_dir_migrates_and_writes_both_halves(mig):
    """``mig149-scratch-migrate-rc`` + ``-record-written`` + ``-workers-written``.

    The record is SPLIT: ``events.jsonl`` and ``workers.json``. Asserting only
    the first would pass on a migration that dropped every worker row, and the
    roster verbs read that half.
    """
    ledger = mig.seed(mig.root / "a")
    state = mig.root / "a" / "state"

    res = mig("--to", "jsonl", dev_state=str(mig.root / "a" / "elsewhere"),
              ledger=ledger)

    assert res.rc == 0, (
        "[mig149-scratch-migrate-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-1500:]))
    assert (state / "events.jsonl").stat().st_size > 0, (
        "[mig149-record-written] events.jsonl is missing or empty")
    assert (state / "workers.json").stat().st_size > 0, (
        "[mig149-workers-written] workers.json is missing or empty — the roster "
        "verbs read that half")


def test_every_row_is_carried_verbatim_across_three_schema_generations(mig):
    """``mig149-row-count-preserved`` + ``-null-n-preserved`` +
    ``-duplicate-n-multiplicity`` + ``-kindless-rows-not-normalised`` +
    ``-legacy-ts-rows-carried``.

    Five traps, each a different way to lose history while looking tidy:

    * a row count that matches but with a row SUBSTITUTED passes the count and
      fails the four shape legs — which is why the count is not enough alone;
    * renumbering an explicit ``null`` ``n`` invents an ordinal the record never
      had, and ordinals are cited by other rows and by reports;
    * deduping a duplicate ``n`` deletes a real event — the collision is
      history, not noise;
    * normalising a kindless row adds a ``kind`` the tool never recorded;
    * dropping a legacy ``ts``/``type``/``text`` row silently ends the oldest
      generation.

    The source is READ BACK and compared, never assumed: a fixture that seeded
    the wrong shape would otherwise make every leg pass against nothing.
    """
    ledger = mig.seed(mig.root / "a")
    state = mig.root / "a" / "state"
    res = mig("--to", "jsonl", dev_state=str(mig.root / "a" / "elsewhere"),
              ledger=ledger)
    assert res.rc == 0, "fixture: the scratch migration failed\n%s" % (
        res.combined[-1200:],)

    src = json.loads(ledger.read_text(encoding="utf-8"))["events"]
    out = _read_jsonl(state / "events.jsonl")

    assert len(src) == len(out), (
        "[mig149-row-count-preserved] %d rows in, %d rows out — the migration "
        "must carry every event, not just the well-formed ones"
        % (len(src), len(out)))

    src_null = sum(1 for e in src if "n" in e and e["n"] is None)
    out_null = sum(1 for e in out if "n" in e and e["n"] is None)
    assert src_null == out_null, (
        "[mig149-null-n-preserved] %d explicit-null ordinals in, %d out — a "
        "renumbered null invents an ordinal the record never had"
        % (src_null, out_null))

    assert _dup_groups(src) == _dup_groups(out), (
        "[mig149-duplicate-n-multiplicity] %d duplicated ordinals in, %d out — "
        "deduping a duplicate n deletes a real event; the collision is history"
        % (_dup_groups(src), _dup_groups(out)))

    src_nk = sum(1 for e in src if "kind" not in e)
    out_nk = sum(1 for e in out if "kind" not in e)
    assert src_nk == out_nk, (
        "[mig149-kindless-rows-not-normalised] %d kindless rows in, %d out — "
        "adding a kind the tool never recorded fabricates history"
        % (src_nk, out_nk))

    src_ts = sum(1 for e in src if "ts" in e)
    out_ts = sum(1 for e in out if "ts" in e)
    assert src_ts == out_ts, (
        "[mig149-legacy-ts-rows-carried] %d legacy ts rows in, %d out — "
        "dropping them silently ends the oldest schema generation"
        % (src_ts, out_ts))


# =============================================================================
# (4) — the view is a function of the record
# =============================================================================
def test_the_view_is_derived_from_the_record_not_copied(mig):
    """``mig149-view-is-derived-from-the-record``.

    ``workers-ledger.json`` after the migration must be reconstructible from
    ``events.jsonl`` + ``workers.json``. A migration that leaves the view a COPY
    of the old blob has moved nothing: the next write still rewrites O(n).

    Compared canonically (sorted keys) because key order is not the claim; the
    CONTENT is.
    """
    ledger = mig.seed(mig.root / "a")
    state = mig.root / "a" / "state"
    res = mig("--to", "jsonl", dev_state=str(mig.root / "a" / "elsewhere"),
              ledger=ledger)
    assert res.rc == 0, "fixture: the scratch migration failed\n%s" % (
        res.combined[-1200:],)

    view = json.loads((state / "workers-ledger.json").read_text(encoding="utf-8"))
    derived = dict(json.loads((state / "workers.json").read_text(encoding="utf-8")))
    derived["events"] = _read_jsonl(state / "events.jsonl")

    assert json.dumps(view, sort_keys=True) == json.dumps(derived, sort_keys=True), (
        "[mig149-view-is-derived-from-the-record] the view is not reconstructible "
        "from the record it was migrated into — it is a copy of the old blob, so "
        "the next write is still O(n).\nview:    %s\nderived: %s"
        % (json.dumps(view, sort_keys=True)[:600],
           json.dumps(derived, sort_keys=True)[:600]))


# =============================================================================
# (5)(6) — refusals that must never write
# =============================================================================
def test_an_existing_record_is_refused_and_force_overwrites_it(mig):
    """``mig149-refuses-existing-record`` + ``mig149-force-overwrites``.

    A second migration over a live record is how a hand-edited JSONL file gets
    silently replaced by a re-derivation from a stale blob. ``--force`` is the
    declared window, and it must actually overwrite rather than being accepted
    and ignored.
    """
    ledger = mig.seed(mig.root / "a")
    dev_state = str(mig.root / "a" / "elsewhere")
    first = mig("--to", "jsonl", dev_state=dev_state, ledger=ledger)
    assert first.rc == 0, "fixture: the first migration failed\n%s" % (
        first.combined[-1200:],)

    again = mig("--to", "jsonl", dev_state=dev_state, ledger=ledger)
    assert again.rc == 2, (
        "[mig149-refuses-existing-record] rc=%s, want 2 — a second migration "
        "must not silently replace an existing record:\n%s"
        % (again.rc, again.combined[-1200:]))

    forced = mig("--to", "jsonl", "--force", dev_state=dev_state, ledger=ledger)
    assert forced.rc == 0, (
        "[mig149-force-overwrites] rc=%s, want 0 — --force is the declared "
        "window over an existing record:\n%s"
        % (forced.rc, forced.combined[-1200:]))


def test_an_unknown_target_and_a_non_json_source_are_refused_without_writing(mig):
    """``mig149-refuses-unknown-target`` + ``-refuses-non-json-source`` +
    ``-non-json-refusal-wrote-nothing``.

    A wrong target name is a usage error (rc 2) and a corrupt source is a DATA
    error (rc 3) — two different verdicts, because one is the operator's typo
    and the other is a record that needs a human. Neither may write anything: a
    partial migration leaves a record that is neither the old blob nor the new
    text, and nothing downstream can tell.
    """
    unknown = mig.seed(mig.root / "b")
    res = mig("--to", "yaml", dev_state=str(mig.root / "b" / "elsewhere"),
              ledger=unknown)
    assert res.rc == 2, (
        "[mig149-refuses-unknown-target] rc=%s, want 2 for an unknown target:\n%s"
        % (res.rc, res.combined[-1200:]))

    bad_state = mig.root / "c" / "state"
    bad_state.mkdir(parents=True, exist_ok=True)
    corrupt = bad_state / "workers-ledger.json"
    corrupt.write_text("not json at all\n", encoding="utf-8")

    res = mig("--to", "jsonl", dev_state=str(mig.root / "c" / "elsewhere"),
              ledger=corrupt)
    assert res.rc == 3, (
        "[mig149-refuses-non-json-source] rc=%s, want 3 — a corrupt source is a "
        "DATA error, not a usage error:\n%s" % (res.rc, res.combined[-1200:]))
    assert not (bad_state / "events.jsonl").exists(), (
        "[mig149-non-json-refusal-wrote-nothing] the refusal still wrote "
        "events.jsonl — a partial migration leaves a record that is neither the "
        "old blob nor the new text")


# =============================================================================
# (7) — the point of the change: a stamp appends one line
# =============================================================================
def test_a_stamp_appends_exactly_one_line_and_it_is_the_last(mig):
    """``mig149-stamp-appends-exactly-one-line`` + ``-appended-row-is-the-last``.

    THE POINT OF THE WHOLE CHANGE. Without this arm the migration could be
    perfect and the write path still O(n) — rewriting the whole blob on every
    stamp — which is the reason the record became text in the first place.

    The second leg matters because a write path that appends one line to the
    WRONG place (or to a second file) satisfies the count and loses the row.
    """
    ledger = mig.seed(mig.root / "a")
    state = mig.root / "a" / "state"
    res = mig("--to", "jsonl", dev_state=str(mig.root / "a" / "elsewhere"),
              ledger=ledger)
    assert res.rc == 0, "fixture: the migration failed\n%s" % (
        res.combined[-1200:],)

    record = state / "events.jsonl"
    before = len(record.read_text(encoding="utf-8").splitlines())

    # The invocation is the SHELL'S, verbatim: OC_LEDGER still points at the
    # SOURCE view (workers-ledger.json), not at events.jsonl. That is the
    # interesting spelling — it is what an un-migrated caller would pass, and it
    # must resolve into JSONL mode and append there. Pointing it at events.jsonl
    # would test the easy path and skip the resolution.
    env = {"OC_NO_FLOODGUARD": "1",
           "OC_ACTOR": "14914914-9149-4914-9149-149149149149",
           "OC_DEV_STATE": str(mig.root / "a" / "elsewhere"),
           "OC_LEDGER": str(ledger)}
    p = mig._run_tool([str(TOOL), "stamp", "note", "mig149 append probe"],
                      timeout=120, env=env)
    assert p.rc == 0, "fixture: the stamp failed rc=%s\n%s" % (
        p.rc, p.combined[-1200:])

    after = len(record.read_text(encoding="utf-8").splitlines())
    assert after == before + 1, (
        "[mig149-stamp-appends-exactly-one-line] %d lines before, %d after — a "
        "stamp must APPEND one line, not rewrite the record" % (before, after))

    last = _read_jsonl(record)[-1]
    assert last.get("what") == "mig149 append probe", (
        "[mig149-appended-row-is-the-last] the appended row is not the last line "
        "of the record — the write path appended to the wrong place: %r"
        % (last,))
