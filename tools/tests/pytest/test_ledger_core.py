"""Ported: the ``oc-ledger`` STORE + LOCK layer, phase 1 (#204).

The bash tool is the fleet's write path, so the Python port cannot be judged by
"it ran" — it is judged by the seven traps a naive reimplementation falls into.
Each one has a leg here, and each leg's docstring says WHICH reading it rules
out, because a test that only asserts rc 0 would pass against a writer that
truncates the log.

The traps, in the order they bite:

1. **A corrupt log must refuse, not skip.** Line-oriented reading silently
   drops a row it cannot parse, and a dropped row reads downstream as "no
   event" — a false ``no claim`` verdict on a real claim.
2. **An append must APPEND.** Rewriting ``events.jsonl`` to add one row opens a
   window where a concurrent reader sees a truncated file, and it rewrites
   every byte of history to add 200.
3. **A non-event mutation must rewrite WHOLESALE** (there is no prefix to
   preserve) while ``workers.json`` is rewritten ONLY when it changed — an
   unconditional rewrite makes every event append look like a roster change.
4. **A lock timeout is rc 4 and NAMES the budget and the knob**, because a
   caller who cannot tell real contention from a stuck holder reaches for the
   wrong remedy.
5. **Two concurrent writers must both land.** The lock exists for this.
6. **A failing git tail must not fail the append.** The row is durable before
   the commit is attempted; conflating them loses rows to a dirty repo.
7. **Legacy mode still loads** — the pre-JSONL single-file shape.

Everything here drives ``ledger_core`` DIRECTLY (it is the ported library) and
``oc-ledger.py`` (the ported CLI) through the shared fixtures, so a divergence
between them fails here rather than in production. The read verbs get their own
differential leg against the bash tool — skipped, never silently passed, when
the bash tool is absent.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import conftest as cf

sys.path.insert(0, str(cf.TOOLS_DIR / "lib"))
import ledger_core as L  # noqa: E402

PY_TOOL = cf.TOOLS_DIR / "state" / "oc-ledger.py"
BASH_TOOL = cf.TOOLS_DIR / "state" / "oc-ledger"

EVENT = {"n": 1, "at": "2026-01-01T00:00:00Z", "event": "note",
         "detail": "a row", "actor": "fixture"}


# ---------------------------------------------------------------------------
# helpers — the fixtures hand us a LEGACY sandbox, the store layer wants JSONL
# ---------------------------------------------------------------------------
def as_jsonl(sandbox, events=(), workers=None):
    """Turn the sandbox into JSONL mode with the given rows.

    ``ledger_sandbox`` ships the pre-JSONL ``workers-ledger.json``; the store
    layer's split-write behaviour only exists in JSONL mode, so a test that
    left the legacy file in place would exercise the other branch entirely and
    report green for the wrong reason.
    """
    state = sandbox.state
    ledger = state / L.EVENTS_NAME
    rows = list(events)
    if not rows:
        # An EMPTY events.jsonl is REFUSED by the bash too ("ledger missing or
        # unparseable" — measured), so a zero-row fixture cannot exercise the
        # write layer at all: it refuses before the transform runs. Seed one
        # bootstrap row instead of pretending an empty file is a valid base.
        rows = [{"n": 1, "event": "bootstrap", "detail": "fixture base"}]
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
    if workers is not None:
        (state / L.WORKERS_NAME).write_text(json.dumps({"workers": workers}))
    os.environ["OC_LEDGER"] = str(ledger)
    return ledger


def read_events(ledger):
    return [json.loads(line) for line in
            Path(ledger).read_text().splitlines() if line.strip()]


def append_one(ledger):
    """A transform that appends exactly one event — the TRUE-APPEND trigger."""
    def transform(doc):
        doc.setdefault("events", []).append(dict(EVENT))
        return None
    return transform


# ---------------------------------------------------------------------------
# trap 1 — a corrupt log REFUSES, and leaves the file byte-identical
# ---------------------------------------------------------------------------
def test_malformed_jsonl_refuses_rc3_and_leaves_the_ledger_untouched(
        ledger_sandbox, run_tool):
    """A skipped corrupt row reads downstream as a MISSING event.

    The leg asserts three things at once, and the third is the one that
    matters: the refusal must not be preceded by a partial write.
    """
    good = json.dumps({"n": 1, "event": "note"})
    ledger = as_jsonl(ledger_sandbox, [])
    ledger.write_text(good + "\n" + "{not json}\n")
    before = ledger.read_bytes()

    res = run_tool([sys.executable, str(PY_TOOL), "events"], timeout=60)

    assert res.rc == 3, \
        "malformed JSONL: rc=%s, want 3 (refused)\n%s" % (res.rc, res.combined)
    # The refusal is the ONE reader's shared text (the bash's too): it names
    # the file and says the record is unparseable. It does NOT carry jq's line
    # diagnostic — that is the `workers`/`worker` path, which prints jq's own
    # stderr line; this path refuses before any projection runs.
    assert "unparseable" in res.combined.lower(), \
        "the refusal must say the record is unparseable, got:\n%s" % res.combined[-600:]
    assert str(ledger) in res.combined, \
        ("the refusal must name the FILE it refused (a bare rc 3 leaves the "
         "caller unable to tell which store is corrupt):\n%s"
         % res.combined[-600:])
    assert ledger.read_bytes() == before, \
        "a refused read MODIFIED the ledger — that is the one thing it may never do"


def test_atomic_write_refuses_a_corrupt_ledger_without_touching_it(ledger_sandbox):
    """Same trap at the writer, where the stake is higher.

    ``atomic_write`` loads before it opens anything for writing, so a corrupt
    record must leave BOTH files byte-identical.
    """
    ledger = as_jsonl(ledger_sandbox, [])
    ledger.write_text('{"n": 1}\n{bad\n')
    before_events = ledger.read_bytes()
    workers = ledger_sandbox.state / L.WORKERS_NAME
    workers.write_text('{"workers": []}')
    before_workers = workers.read_bytes()

    with pytest.raises(L.LedgerError) as excinfo:
        L.atomic_write(str(ledger), append_one(str(ledger)))

    assert excinfo.value.rc == L.RC_REFUSED, \
        "corrupt load: rc=%s, want 3" % excinfo.value.rc
    assert ledger.read_bytes() == before_events, \
        "the refused write modified events.jsonl"
    assert workers.read_bytes() == before_workers, \
        "the refused write modified workers.json"


# ---------------------------------------------------------------------------
# trap 2 — an append APPENDS (prefix preserved, exactly one line added)
# ---------------------------------------------------------------------------
def test_single_event_append_grows_one_line_and_preserves_the_prefix(
        ledger_sandbox):
    """Prefix equality is the assertion, not "the row is present".

    A wholesale rewrite also ends with the row present — so only the PREFIX
    distinguishes an append from a rewrite, and the rewrite is the shape that
    opens a truncation window for concurrent readers.
    """
    first = {"n": 1, "event": "note", "detail": "pre-existing"}
    ledger = as_jsonl(ledger_sandbox, [first])
    before = ledger.read_bytes()
    assert before.endswith(b"\n"), "fixture must end with a newline"

    L.atomic_write(str(ledger), append_one(str(ledger)))

    after = ledger.read_bytes()
    assert after.startswith(before), \
        ("the pre-existing bytes are no longer a PREFIX of the file — that is a "
         "wholesale rewrite wearing an append's clothes:\nbefore=%r\nafter=%r"
         % (before[-120:], after[:len(before) + 120]))
    assert len(after.splitlines()) == len(before.splitlines()) + 1, \
        "one append must add exactly one line"
    assert read_events(ledger)[-1]["detail"] == "a row"


def test_append_does_not_touch_workers_json_when_only_events_changed(
        ledger_sandbox):
    """``workers.json`` is rewritten ONLY when it changed (the bash's ``cmp``).

    An unconditional rewrite makes every append look like a roster change and
    hands every concurrent roster reader a needless new inode.
    """
    workers = [{"uuid": "hq", "role": "hq", "topic_id": 4, "state": "ACTIVE"}]
    ledger = as_jsonl(ledger_sandbox, [], workers=workers)
    wpath = ledger_sandbox.state / L.WORKERS_NAME
    before = wpath.read_bytes()
    inode = wpath.stat().st_ino

    L.atomic_write(str(ledger), append_one(str(ledger)))

    assert wpath.read_bytes() == before, "workers.json content changed"
    assert wpath.stat().st_ino == inode, \
        ("workers.json was REPLACED (new inode) although no worker changed — "
         "the split rule says it is rewritten only when it differs")


# ---------------------------------------------------------------------------
# trap 3 — a non-event mutation rewrites WHOLESALE
# ---------------------------------------------------------------------------
def test_non_event_mutation_rewrites_wholesale_and_writes_workers(
        ledger_sandbox):
    """No prefix to preserve, and the roster change must land."""
    ledger = as_jsonl(ledger_sandbox, [{"n": 1, "event": "note"}])

    def transform(doc):
        doc.setdefault("workers", []).append(
            {"uuid": "aaaa", "role": "editor", "topic_id": 9})
        return None

    L.atomic_write(str(ledger), transform)

    workers = json.loads((ledger_sandbox.state / L.WORKERS_NAME).read_text())
    assert workers["workers"][0]["uuid"] == "aaaa", \
        "the roster change did not reach workers.json"
    assert read_events(ledger) == [{"n": 1, "event": "note"}], \
        "a roster mutation must not disturb the event log"


# ---------------------------------------------------------------------------
# trap 4 — lock timeout is rc 4 and names the budget AND the knob
# ---------------------------------------------------------------------------
@pytest.mark.serial
@pytest.mark.xdist_group("battery-ledger-lock")
def test_lock_timeout_is_rc4_naming_the_budget_and_the_knob(
        ledger_sandbox, monkeypatch):
    """rc 4, and the message must carry BOTH the budget and ``OC_LEDGER_LOCK_WAIT``.

    A bare "timeout" leaves the caller guessing between three remedies — real
    contention, a pre-#641 inherited fd, a holder stuck on I/O — and the knob
    is the only one of the three they can turn.
    """
    import fcntl

    ledger = as_jsonl(ledger_sandbox, [])
    lock_path = str(ledger) + ".lock"
    monkeypatch.setenv("OC_LEDGER_LOCK_WAIT", "1")

    holder = open(lock_path, "w")
    try:
        fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(L.LockTimeout) as excinfo:
            with L._LedgerLock(str(ledger)):
                pass
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()

    message = str(excinfo.value)
    assert excinfo.value.rc == L.RC_IO, \
        "lock timeout rc=%s, want 4" % excinfo.value.rc
    assert "1s" in message, \
        "the refusal must name the budget it waited (%r)" % message
    assert "OC_LEDGER_LOCK_WAIT" in message, \
        "the refusal must name the knob that raises it (%r)" % message


# ---------------------------------------------------------------------------
# trap 5 — two concurrent writers, no row lost
# ---------------------------------------------------------------------------
@pytest.mark.serial
@pytest.mark.xdist_group("battery-ledger-lock")
def test_two_concurrent_writers_lose_no_row(ledger_sandbox):
    """Both writers must land, and each row must be whole.

    Run as two real processes through the CLI's writer path rather than two
    threads: flock is per open-file-description, so threads in one process
    would share an fd and the test would prove nothing about the fleet.
    """
    ledger = as_jsonl(ledger_sandbox, [])
    script = (
        "import sys, json;"
        "sys.path.insert(0, %r);"
        "import ledger_core as L;"
        "led = %r;"
        "tag = sys.argv[1];"
        "L.atomic_write(led, lambda d: d.setdefault('events', []).append("
        "{'n': len(d.get('events') or []) + 1, 'event': 'note', 'tag': tag}))"
        % (str(cf.TOOLS_DIR / "lib"), str(ledger))
    )
    env = dict(os.environ)
    env["OC_LEDGER"] = str(ledger)
    env["OC_TOOLS_NOLOG"] = "1"
    procs = [subprocess.Popen([sys.executable, "-c", script, tag],
                              env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
             for tag in ("alpha", "beta")]
    outs = [p.communicate(timeout=120) for p in procs]

    for proc, (out, err) in zip(procs, outs):
        assert proc.returncode == 0, \
            "a concurrent writer failed rc=%s\n%s" % (
                proc.returncode, err.decode("utf-8", "replace")[-800:])

    tags = sorted(row.get("tag") for row in read_events(ledger)
                  if row.get("tag") is not None)
    assert tags == ["alpha", "beta"], \
        ("two concurrent appends must both land — got %r (a lost row is the "
         "exact failure the lock exists to prevent)" % (tags,))
    ns = sorted(row["n"] for row in read_events(ledger))
    # The fixture base holds n=1, so the two writers must number 2 and 3.
    assert ns == [1, 2, 3], \
        ("each writer numbered from the live length, so the two rows must be "
         "n=2,3 over the base's n=1 — got %r (a DUPLICATE n means both read "
         "the same base, which is the lost-update the lock prevents)" % (ns,))
    assert len(set(ns)) == len(ns), "duplicate n in %r" % (ns,)


# ---------------------------------------------------------------------------
# trap 6 — a failing git tail must not fail the append
# ---------------------------------------------------------------------------
def test_git_tail_failure_does_not_fail_the_append(ledger_sandbox, monkeypatch):
    """The row is durable BEFORE the commit is attempted; never conflate them.

    A dirty or broken state repo must cost a warning, never a row. The commit
    itself is made to fail here (not ``os.open``, which the LEDGER lock needs
    as well — patching that failed the lock and proved nothing about the tail).
    """
    ledger = as_jsonl(ledger_sandbox, [])
    before = ledger.read_bytes()

    def boom(*args, **kwargs):
        raise OSError("simulated: the state commit cannot run")

    monkeypatch.setattr(L, "_git_state_commit_now", boom)

    # git_state_commit QUEUES under the lock; flush_git_tail drains it.
    with L._LedgerLock(str(ledger)):
        L.git_state_commit(str(ledger), "state: simulated")
        assert L.pending_git_messages(), \
            "git_state_commit under the lock must QUEUE, not run"
    L.flush_git_tail(str(ledger), wait=1)      # must warn, must not raise

    assert not L.pending_git_messages(), \
        "the tail must drain its queue even when it cannot commit"
    assert ledger.read_bytes() == before, \
        "the failed tail must not have touched the event log"


def test_git_tail_failure_leaves_the_appended_row_durable(ledger_sandbox):
    """The end-to-end shape: append under the lock, tail fails, row survives."""
    ledger = as_jsonl(ledger_sandbox, [{"n": 1, "event": "note"}])
    before = ledger.read_bytes()

    L.atomic_write(str(ledger), append_one(str(ledger)))
    # A tail over a non-repo state dir is the natural failure; it warns only.
    L.git_state_commit(str(ledger), "state: after append")
    L.flush_git_tail(str(ledger), wait=1)

    after = ledger.read_bytes()
    assert after.startswith(before), "the appended row was lost"
    assert len(read_events(ledger)) == 2


# ---------------------------------------------------------------------------
# trap 7 — legacy mode still loads
# ---------------------------------------------------------------------------
def test_legacy_mode_loads_the_single_file_shape(ledger_sandbox):
    """Pre-JSONL ``workers-ledger.json`` must still read AND write.

    ``jsonl_mode`` keys off ``events.jsonl``; the sandbox ships the legacy file,
    so this leg is the one that proves the fallback branch is wired rather than
    merely present.
    """
    legacy = ledger_sandbox.ledger
    assert not L.jsonl_mode(str(legacy)), \
        "the sandbox fixture must be legacy mode for this leg to mean anything"

    doc = L.load_ledger(str(legacy))
    assert doc.get("workers"), "the legacy fixture's workers did not load"
    assert L.max_n(str(legacy)) == 0, "the legacy fixture holds no events"

    L.atomic_write(str(legacy), append_one(str(legacy)))

    doc = json.loads(legacy.read_text())
    assert len(doc.get("events") or []) == 1, \
        "the legacy write did not append the event"


# ---------------------------------------------------------------------------
# the read verbs — differential against the bash tool
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not BASH_TOOL.is_file(),
                    reason="the bash oc-ledger is not in this checkout")
@pytest.mark.parametrize("argv", [
    ("--verbs",),
    ("events",),
    ("tail",),
    ("tail", "--n", "2"),
    ("workers",),
    ("workers", "--tsv"),
    ("workers", "--json"),
    ("roster",),
    ("roster", "--json"),
    ("lessons",),
    ("claims",),
    ("mode",),
    ("ok",),
    ("duplicates",),
    ("cadence",),
    ("law-digest",),
    ("--help",),
    ("frobnicate",),
])
def test_read_verbs_are_byte_identical_to_the_bash(ledger_sandbox, run_tool,
                                                   argv):
    """rc, stdout AND stderr must match, verb by verb.

    A port that matches on stdout alone passes while printing a different
    refusal to stderr, and every lane that pipes the tool's stderr into a
    report then quotes a diagnostic the bash never wrote.
    """
    env = {
        "OC_LEDGER": str(ledger_sandbox.ledger),
        "OC_SKILL_DIR": str(ledger_sandbox.skill),
        "OC_TOOLS_NOLOG": "1",
    }
    bash = run_tool([str(BASH_TOOL), *argv], timeout=60, env=env)
    py = run_tool([sys.executable, str(PY_TOOL), *argv], timeout=60, env=env)

    assert (py.rc, py.out, py.err) == (bash.rc, bash.out, bash.err), (
        "verb %r diverges from the bash port\n"
        "  rc     bash=%r py=%r\n"
        "  stdout bash=%r py=%r\n"
        "  stderr bash=%r py=%r"
        % (" ".join(argv), bash.rc, py.rc,
           bash.out[-400:], py.out[-400:],
           bash.err[-400:], py.err[-400:]))


@pytest.mark.parametrize("rows", [
    ('{"workers":[{"uuid":"a"}]}\n5\n{"workers":[{"uuid":"b"}]}\n',
     "good,bad,good: jq's exit is the LAST document's, so rc 0 and BOTH arrays"),
    ('{"workers":[{"uuid":"a"}]}\n5\n',
     "good,bad: rc 3 and the good array is DISCARDED with the failure"),
    ('5\n{"workers":[{"uuid":"a"}]}\n',
     "bad,good: rc 0 — an early failure does not poison a later success"),
    ('null\ntrue\n{"workers":"x"}\n',
     "null is INDEXABLE in jq; true is not; a non-array .workers passes through"),
])
def test_workers_stream_semantics_match_the_bash(ledger_sandbox, run_tool, rows):
    """The jq-stream reading, which is where the first port diverged.

    ``workers`` over a multi-row record prints one array PER DOCUMENT, and the
    exit status follows the last one — not "any failure fails the verb" and not
    "the first failure aborts the scan". Both of those wrong readings were real
    bugs found by this differential, so both are pinned here.
    """
    text, why = rows
    ledger = as_jsonl(ledger_sandbox, [])
    ledger.write_text(text)
    env = {"OC_LEDGER": str(ledger),
           "OC_SKILL_DIR": str(ledger_sandbox.skill),
           "OC_TOOLS_NOLOG": "1"}

    bash = run_tool([str(BASH_TOOL), "workers"], timeout=60, env=env)
    py = run_tool([sys.executable, str(PY_TOOL), "workers"], timeout=60, env=env)

    assert (py.rc, py.out, py.err) == (bash.rc, bash.out, bash.err), (
        "%s\n  rc     bash=%r py=%r\n  stdout bash=%r py=%r\n  stderr "
        "bash=%r py=%r" % (why, bash.rc, py.rc, bash.out, py.out,
                           bash.err, py.err))
