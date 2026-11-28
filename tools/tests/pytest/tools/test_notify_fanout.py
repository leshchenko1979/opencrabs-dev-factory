"""`oc-notify-fanout` guards: law 1, dead targets, --roles.

The section exists because the tool's own ``--selftest`` counts ONE case however
many assertions it makes internally: a wave that reaches nobody while reporting
success is invisible to it. Three legs, each a different way a wave LOOKS clean
and is not:

* **61a law 1 — placeholder-token guard.** A brief that still carries ``{{TOK}}``
  after substitution is a brief no lane can act on. Every send must ABORT and the
  wave must exit non-zero. The failure it prevents is the quiet one: ``sent=N``
  while every lane received a literal ``{{NOSUCH}}``.
* **61b substitution.** ``{{UUID}}`` / ``{{VERSION}}`` must resolve and no ABORT
  may fire. The twin of 61a, so "fix 61a by deleting the guard" reddens here.
* **61c ``--roles``.** With the invoker's own role as the only selector, the wave
  must reach NOBODY: the roster row matches, and self-exclusion is what keeps it
  from being sent to. A leg using ``--roles editor`` cannot tell those apart.

The tool's own ``--selftest`` is driven here ONCE, slow-marked, as the factory
#212 regression (§61d). Factory #203 kept it out of the DEFAULT gate because it
costs ~4.5 min; ``-m "not slow"`` preserves that exclusion exactly while leaving
the case runnable on request. See the SCOPE note at the end of this file.

**Counters are read as FIELDS, never substrings.** ``absent=1`` CONTAINS
``sent=1``, so the shell's ``grep -q 'sent=1'`` arm is satisfied by a wave that
merely disclosed an absence — it can never go red in exactly the case it was
written for (a mutation that drives ``sent`` to 2 still satisfies the substring
arm). ``_field`` anchors on a key boundary.

**DEVIATION from the shell harness, deliberate: this module touches NO live
state.** The shell section resolved the invoker with ``oc-ledger roster
--live`` and pointed ``OC_FANOUT_LEDGER`` at the LIVE fleet ledger, so each of
its four legs wrote real fleet state and its verdict depended on which lanes
exist on the box today.
Here the invoker is a fixture uuid, the roster is a fixture JSON and the session
DB is a throwaway, so the same four claims hold on any box and no leg can flip
because a lane was retired. ``OC_FANOUT_RUN_DIR`` is redirected as well: the
tool's production default is ``<skill>/run`` and the wave id is DERIVED FROM THE
BRIEF TEXT, so two concurrent instances collide on one lock there (the
``rc 7``/``rc 4`` class the tool's own selftest comment records).
"""

from __future__ import annotations

import json
import re
import sqlite3

import pytest

import conftest as cf

NF = cf.tool_path("oc-notify-fanout")

FORUM = "-1999999999"

LANE_1 = "11111111-1111-4111-8111-111111111111"   # editor
LANE_2 = "22222222-2222-4222-8222-222222222222"   # editor
LANE_T = "33333333-3333-4333-8333-333333333333"   # toolsmith — the invoker

# Matches no real lane, so a leaked self can never silently exclude someone.
SELF_ABSENT = "00000000-0000-4000-8000-00000000dead"


def _field(name, text):
    """The LAST ``name=N`` in the tool's output, or ``None``.

    Anchored on a key boundary: ``absent=1`` must not satisfy a ``sent`` check.
    """
    hits = re.findall(r"(?:^|\s)%s=(\d+)" % re.escape(name), text, re.M)
    return int(hits[-1]) if hits else None


@pytest.fixture
def wave(tmp_path):
    """A fan-out sandbox: fixture roster, throwaway session DB, isolated run dir.

    Built under ``tmp_path``, NOT ``scratch``: the scratch root is SESSION-scoped,
    so a fixed subdirectory name is reused across tests and the second
    ``CREATE TABLE sessions`` lands in an existing DB (the same trap ``git_repo``
    documents for named repos).

    Three live sessions, all bound to one forum chat, so ``--roles`` is the only
    thing that can shrink the target set — ``sent=3`` reached everyone and
    ``sent=0`` reached nobody.
    """
    root = tmp_path / "notify-fanout"
    root.mkdir(parents=True, exist_ok=True)

    db = root / "sessions.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT, archived_at INTEGER,
                       updated_at INTEGER DEFAULT 0);
CREATE TABLE session_bindings (session_id TEXT PRIMARY KEY, channel TEXT,
                               chat_id TEXT, thread_id INTEGER,
                               updated_at INTEGER DEFAULT 0);
INSERT INTO sessions VALUES ('%s','lane1',NULL,strftime('%%s','now'));
INSERT INTO sessions VALUES ('%s','lane2',NULL,strftime('%%s','now'));
INSERT INTO sessions VALUES ('%s','toolsmith',NULL,strftime('%%s','now'));
INSERT INTO session_bindings VALUES ('%s','telegram','%s',1,0);
INSERT INTO session_bindings VALUES ('%s','telegram','%s',2,0);
INSERT INTO session_bindings VALUES ('%s','telegram','%s',3,0);
""" % (LANE_1, LANE_2, LANE_T, LANE_1, FORUM, LANE_2, FORUM, LANE_T, FORUM))
    con.commit()
    con.close()

    ledger = root / "roster.json"
    ledger.write_text(json.dumps({"workers": [
        {"uuid": LANE_1, "role": "editor", "topic_id": 1},
        {"uuid": LANE_2, "role": "editor", "topic_id": 2},
        {"uuid": LANE_T, "role": "toolsmith", "topic_id": 3},
    ], "events": []}, indent=1) + "\n")

    run_dir = root / "run"
    run_dir.mkdir()

    return cf.Node(root, db=db, ledger=ledger, run_dir=run_dir)


def _env(wave, self_uuid=SELF_ABSENT, **extra):
    """Every path inline; nothing inherited from the fleet."""
    env = {
        "OC_FANOUT_LEDGER": str(wave.ledger),
        "OC_NOTIFY_DB": str(wave.db),
        "OC_FANOUT_FORUM_CHAT": FORUM,
        "OC_FANOUT_SELF": self_uuid,
        "OC_FANOUT_RUN_DIR": str(wave.run_dir),
        "OC_TOOLS_NOLOG": "1",
    }
    env.update(extra)
    return env


def _wave(run_tool, wave, *argv, self_uuid=SELF_ABSENT):
    return run_tool([str(NF), *argv], timeout=200,
                    env=_env(wave, self_uuid=self_uuid))


# =============================================================================
# 61a. law 1 — a dangling token ABORTs every send
# =============================================================================
def test_dangling_placeholder_aborts_every_send(run_tool, wave):
    """A brief carrying ``{{NOSUCH}}`` must not reach one lane, and the wave
    must not exit 0: a green rc here is the silent-delivery defect."""
    res = _wave(run_tool, wave, "--title", "t-battery",
                "--text", "dangling {{NOSUCH}} token",
                "--dry-run", "--no-stamp")

    assert res.rc != 0, (
        "law 1: rc=0 on a brief whose placeholder SURVIVED substitution — every "
        "lane would have received a literal {{NOSUCH}}:\n%s"
        % res.combined[-900:])
    assert "placeholder-token-survived" in res.combined, (
        "the wave aborted but emitted no law-1 receipt, so an operator cannot "
        "tell a guard from a crash:\n%s" % res.combined[-900:])
    assert _field("sent", res.combined) == 0, (
        "law 1 aborted on paper yet counted sent=%s:\n%s"
        % (_field("sent", res.combined), res.combined[-900:]))
    assert _field("failed", res.combined) == 3, (
        "want failed=3 (one ABORT per target), got %s:\n%s"
        % (_field("failed", res.combined), res.combined[-900:]))
    assert "DRY " not in res.combined, (
        "a target reached a DRY receipt after the law-1 abort — the guard fired "
        "per-target and the wave carried on:\n%s" % res.combined[-900:])


# =============================================================================
# 61b. substitution — valid tokens resolve, nothing aborts
# =============================================================================
def test_valid_tokens_substitute_and_nothing_aborts(run_tool, wave):
    """The twin of 61a: deleting the guard to make 61a pass reddens THIS leg."""
    res = _wave(run_tool, wave, "--title", "t-battery",
                "--text", "v{{VERSION}} u{{UUID}}",
                "--dry-run", "--no-stamp")

    assert res.rc == 0, "substitution rc=%s\n%s" % (res.rc, res.combined[-900:])
    assert "placeholder-token-survived" not in res.combined, (
        "{{UUID}}/{{VERSION}} were NOT substituted — the guard fired on legal "
        "tokens:\n%s" % res.combined[-900:])
    assert _field("sent", res.combined) == 3, (
        "want sent=3 (every forum-bound lane), got %s:\n%s"
        % (_field("sent", res.combined), res.combined[-900:]))
    assert _field("failed", res.combined) == 0, (
        "a dry wave reported failed=%s with no dead targets in the roster:\n%s"
        % (_field("failed", res.combined), res.combined[-900:]))


# =============================================================================
# 61c. --roles — self is excluded, so a toolsmith wave reaches nobody
# =============================================================================
def test_roles_filter_excludes_the_invoking_lane(run_tool, wave):
    """``--roles toolsmith`` from the toolsmith itself: the roster HAS a matching
    row and the wave must still reach nobody.

    This is what separates "the filter works" from "the filter matched and
    self-exclusion works" — with ``--roles editor`` a broken self-exclusion would
    still read sent=2, so the toolsmith is the discriminating choice.
    """
    res = _wave(run_tool, wave, "--title", "t", "--text", "x",
                "--dry-run", "--no-stamp", "--roles", "toolsmith",
                self_uuid=LANE_T)

    assert res.rc == 0, "roles rc=%s\n%s" % (res.rc, res.combined[-600:])
    assert _field("sent", res.combined) == 0, (
        "self was NOT excluded: a toolsmith-only wave sent to %s lane(s):\n%s"
        % (_field("sent", res.combined), res.combined[-900:]))
    assert _field("skipped", res.combined) == 0, (
        "the self-excluded lane was counted as SKIPPED (%s) — self-exclusion is a "
        "filter, not a per-target skip, and conflating them inflates every wave's "
        "skip count:\n%s" % (_field("skipped", res.combined), res.combined[-900:]))

# =============================================================================
# 61d. factory #212 — the selftest must never abort SILENTLY
# =============================================================================
# The defect: ``oc-notify-fanout --selftest`` exited rc 3 with 0 bytes on stdout
# AND 0 bytes on stderr when ``OC_DEV_STATE`` named a directory with no
# ``events.jsonl``. ``set -euo pipefail`` killed the body at an unguarded
# non-zero exit before the summary line, so an operator saw the same three bytes
# a SIGKILL produces and four sessions filed it as a resource flake. Three
# changes fixed it in the tool: an ERR trap that names line + command, ledger
# isolation on the two arms that inherited ambient env, and a red-gate that
# disarms the trap so a legitimately-red selftest exits quietly.
#
# WHY THE BATTERY CANNOT REPRODUCE IT BY ACCIDENT: ``env_guard`` materialises
# ``OC_DEV_STATE/events.jsonl`` (conftest, the "must be MATERIALISED, not merely
# named" note), so the ledger-less condition can only be built by the leg itself
# — which is what ``test_selftest_never_aborts_silently`` does.
#
# The guard leg is STATIC on purpose. The failure class is SILENCE, and it can
# only be observed from outside by re-breaking the isolation that was just
# fixed — a leg that did so would be asserting on a mutation of the subject.
# Reading the source for the trap's presence and reachability tests the guard
# itself, which is the claim that can be checked without editing the tool.

@pytest.mark.slow
@pytest.mark.serial
@pytest.mark.xdist_group("tool-selftests")
def test_selftest_never_aborts_silently(run_tool, tmp_path):
    """``--selftest`` against a ledger-LESS ``OC_DEV_STATE``: rc 0, ``FAIL=0``.

    Pre-fix this exact invocation was rc 3 with nothing on either stream. The
    ``env -u`` prefix is the faithful reproduction, not a convenience:
    ``oc_ledger_path`` (tools/lib/oc-log.sh) reads ``OC_LEDGER > OC_DEV_STATE >
    $HOME``, so an ambient ``OC_LEDGER``/``OC_FANOUT_LEDGER`` would supply a
    path and the ledger-less condition would never be reached.

    Slow-marked (~4.5 min) and pinned to the ``tool-selftests`` group: pytest.ini
    deselects ``slow`` from the gate (factory #203's exclusion, preserved), and
    the group keeps this instance from overlapping the wrapper blanket's.
    """
    ledgerless = tmp_path / "dev-state-without-events"
    ledgerless.mkdir()                      # a directory, deliberately EMPTY

    res = run_tool(
        ["env", "-u", "OC_LEDGER", "-u", "OC_FANOUT_LEDGER",
         str(NF), "--selftest"],
        timeout=600,
        env={"OC_DEV_STATE": str(ledgerless)},
    )

    assert not res.timed_out, (
        "--selftest hit the 600 s bound (a hang, not a verdict) — #753 class")
    assert res.rc == 0, (
        "factory #212: --selftest with a ledger-less OC_DEV_STATE exited rc=%s "
        "(%d bytes stdout, %d bytes stderr). A non-zero rc here is the defect "
        "UNLESS it names itself — check for a SELFTEST ABORT line, which is the "
        "guard doing its job and means a real arm broke:\n%s"
        % (res.rc, len(res.out), len(res.err), res.combined[-1500:]))
    assert "SELFTEST ABORT" not in res.combined, (
        "the ERR trap fired on a run that should be green — an arm aborted:\n%s"
        % res.combined[-1500:])
    assert "FAIL=0" in res.out, (
        "want the summary line 'oc-notify-fanout selftest: PASS=<n> FAIL=0' on "
        "STDOUT; got %d bytes stdout:\n%s" % (len(res.out), res.combined[-1500:]))
    assert _field("FAIL", res.out) == 0, (
        "FAIL=%s in the summary — the selftest is legitimately red and this leg "
        "must not paper over it:\n%s"
        % (_field("FAIL", res.out), res.combined[-1500:]))

def _selftest_branch(src):
    """``(start, end)`` line indices of the ``--selftest`` branch, ``fi`` inclusive.

    The branch opens with the argv dispatch and closes on the first column-0
    ``fi`` — nesting inside it is indented, so a column-0 ``fi`` is the boundary.
    """
    start = next(i for i, ln in enumerate(src)
                 if ln.startswith('if [ "${1:-}" = "--selftest" ]; then'))
    end = next(i for i in range(start + 1, len(src))
               if src[i].rstrip("\n") == "fi")
    return start, end

def test_selftest_reports_abort_instead_of_silence():
    """The GUARD: an ERR trap inside the ``--selftest`` branch, and a disarm.

    Two claims, both about silence rather than about any single arm:

    1. ``trap '...SELFTEST ABORT...' ERR`` is REGISTERED between the ``--selftest``
       dispatch and its closing ``fi``. Outside that branch it would never arm;
       inside, any unguarded non-zero exit names its line and command instead of
       dying with 0 bytes on both streams.
    2. The final gate disarms it (``trap - ERR``) before exiting non-zero, so a
       legitimately-red selftest prints its FAIL lines and exits QUIETLY — an
       ABORT line appended after a real FAIL summary would send the next reader
       hunting a phantom crash.

    Static by design: see the §61d note above for why the class cannot be
    observed from outside without re-breaking the isolation it protects.
    """
    src = NF.read_text().splitlines(keepends=True)
    start, end = _selftest_branch(src)
    branch = src[start:end + 1]
    where = "lines %d-%d" % (start + 1, end + 1)

    trap_lines = [ln for ln in branch if "SELFTEST ABORT" in ln]
    assert trap_lines, (
        "factory #212: no 'SELFTEST ABORT' ERR trap inside the --selftest "
        "branch (%s). Without it an unguarded non-zero exit is rc 3 with 0 "
        "bytes on BOTH streams — indistinguishable from a SIGKILL." % where)
    trap = trap_lines[0]
    assert trap.lstrip().startswith("trap "), (
        "the SELFTEST ABORT text is not a trap registration: %r" % trap.strip())
    assert trap.rstrip().endswith("ERR"), (
        "the trap is not bound to ERR, so it cannot see a `set -e` abort: %r"
        % trap.strip())
    for token, why in (("LINENO", "the aborting LINE"),
                       ("BASH_COMMAND", "the aborting COMMAND")):
        assert token in trap, (
            "the ERR trap does not name %s ($%s), so the message says only that "
            "something died: %r" % (why, token, trap.strip()))

    disarm = [ln for ln in branch if "trap - ERR" in ln]
    assert disarm, (
        "factory #212: the red gate no longer disarms the ERR trap (%s). A red "
        "selftest would then print its FAIL lines AND a misleading SELFTEST "
        "ABORT line, which reads as a crash rather than a verdict." % where)
    assert any(ln.lstrip().startswith('[ "$F" -eq 0 ]') for ln in disarm), (
        "the trap disarm is not the red gate ('[ \"$F\" -eq 0 ] || { trap - ERR; "
        "exit 1; }'): %r" % disarm[0].strip())

def test_selftest_arms_pin_the_ledger():
    """The two ISOLATION edits, asserted where they live.

    ``oc_ledger_path`` precedence is ``OC_LEDGER > OC_DEV_STATE > $HOME``
    (tools/lib/oc-log.sh), so an inherited ``OC_DEV_STATE`` DEFEATS an arm that
    only fakes ``HOME``, and an arm that pins nothing resolves the ambient env.
    Both were measured failures in #212:

    * arm 1a2 (law-17 holder scan) faked ``HOME`` and was killed at the roster
      check by the inherited ``OC_DEV_STATE`` — it must ``env -u`` all three
      ledger vars, and carry ``|| true`` so a recurrence is reported by the
      ``chk`` that owns the claim rather than as a silent abort.
    * the ``text-file-missing-rc2`` leg measured ``got rc=3`` (the exact line in
      the issue body) because it pinned no ledger at all — it must pass
      ``OC_FANOUT_LEDGER="$LEDG"`` to the child.
    """
    src = NF.read_text().splitlines()

    # --- arm 1a2: the law-17 holder scan that fakes HOME -------------------
    a = next((i for i, ln in enumerate(src)
              if 'out="$(env -u OC_FANOUT_LEDGER' in ln), None)
    assert a is not None, (
        "arm 1a2 (law-17 holder scan) no longer unsets OC_FANOUT_LEDGER at all — "
        "it cannot be running with a controlled ledger")
    stmt = "\n".join(src[a:a + 8])
    for var in ("OC_DEV_STATE", "OC_LEDGER"):
        assert "-u %s" % var in stmt, (
            "factory #212: arm 1a2 does not `env -u %s`. An inherited value "
            "outranks the arm's fake HOME in oc_ledger_path and kills it rc 3 at "
            "the roster check before any assertion runs:\n%s" % (var, stmt))
    assert "|| true" in stmt, (
        "arm 1a2 is not guarded with `|| true`, so a recurrence kills the whole "
        "selftest at the assignment (set -e) instead of reddening the chk that "
        "owns the claim:\n%s" % stmt)

    # --- text-file-missing-rc2: pins the ledger on the child --------------
    t = next((i for i, ln in enumerate(src)
              if '--text-file "$T/does-not-exist.md"' in ln), None)
    assert t is not None, (
        "the text-file-missing-rc2 invocation is gone — this leg has no subject")
    call = "\n".join(src[max(0, t - 4):t + 1])
    assert 'OC_FANOUT_LEDGER="$LEDG"' in call, (
        "factory #212: text-file-missing-rc2 does not pin OC_FANOUT_LEDGER. It "
        "then measures the AMBIENT env, reports `got rc=3` from the roster check "
        "and looks like a missing-rc-2 defect:\n%s" % call)
    assert '[ "$rc_mf" = 2 ]' in src[t + 1] if t + 1 < len(src) else False, (
        "the rc-2 assertion that follows the pinned invocation is gone:\n%s"
        % "\n".join(src[t:t + 2]))

# =============================================================================
# SCOPE — what this module deliberately does NOT do
# =============================================================================
# Factory #203 removed the blanket ``run_selftest oc-notify-fanout`` leg from
# this module: ``tools/test_tool_wrappers.py`` already drives the same
# ``--selftest`` as one parametrised case, slow-marked, at ~266 s, and driving it
# twice buys one extra ``rc == 0`` for four and a half minutes.
#
# §61d is the ONE exception, and it is not the deleted leg: it drives the
# selftest under a condition the blanket CANNOT build (a ledger-less
# ``OC_DEV_STATE`` — env_guard materialises the file) and asserts a claim the
# blanket does not make (``FAIL=0`` on stdout, no ABORT). It stays slow-marked,
# so the default gate is still exactly as fast as #203 left it.
