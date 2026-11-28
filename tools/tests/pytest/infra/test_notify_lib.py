"""`lib/oc-notify.sh` — the CLI budget (#466) and the fallback leg (#472/#18).

Two defects, and both are the same shape: a code path that could not be reached,
so its absence read as its success.

§57 — THE FALLBACK WAS UNREACHABLE BY CONSTRUCTION. ``oc_notify_session`` tries
the CLI, then falls back to a direct A2A JSON-RPC call *only on a non-zero rc*.
With no budget of its own, a hung ``session notify`` blocks forever — so the
fallback existed for exactly the case that prevented it from ever running. The
fix gives the CLI leg a bound; a timeout exits **124**, which is not 0/2/3, so a
hung CLI now falls THROUGH to the A2A leg. The discriminating input is a stub
that sleeps 30 s under a 2 s budget: elapsed must be ~2 s, the A2A leg must be
REACHED, and the rc must stay the ambiguous **124** — never 0/2/3, which would
read as a delivery verdict.

§58 — TWO defects in one fallback, both about a receipt nobody should trust:

  A (#472) the ``(target, window)`` journal fallback was TARGET-scoped, so any
    delivery to the same lane inside the window could settle a send that never
    landed (Triage 41ca47a9: #433's row settled #466). The caller supplies a
    per-SEND sender label and owns the stricter, identity-keyed receipt check,
    so this lib must forward that label as ``--sender``.
  B (#18) that same fallback was INERT: its status was captured with ``||``,
    which fires ONLY on failure, so the variable kept its initial value on the
    SUCCESS path and a matching journal row still returned the transport's rc.

It is DELETED, not repaired. The discriminating input is a journal row that
MATCHES the target on every field — pre-#18 that row was the fallback's whole
purpose, so if the fallback ever returns the rc flips to 0 AND the marker
appears. The ``python3`` stub records WHICH python leg ran, so "the lib
inspected the journal" stays observable even though the path is gone.
"""

from __future__ import annotations

import pytest

import conftest as cf

LIB = cf.TOOLS_DIR / "lib" / "oc-notify.sh"
UUID = "00000000-0000-4000-8000-000000000000"

# A notify binary that HANGS, and says so if it is killed.
HANGING_BIN = """#!/bin/sh
echo "invoked" >> "$MARK"
trap 'echo killed >> "$MARK"; exit 143' TERM
sleep 30
"""

# A python3 that records ENTRY to the A2A leg without opening a socket to the
# live gateway — whose availability is a host fact, not a property of this code,
# so a real call would make the leg pass or fail for the wrong reason.
A2A_ONLY = """#!/bin/sh
echo "a2a" >> "$MARK"
exit 4
"""

# The same seam, but its journal arm exits 0 deliberately: if the deleted
# fallback comes back, that arm makes the function return 0, so the rc leg fails
# as well as the marker leg.
A2A_WITH_JOURNAL_ARM = """#!/bin/sh
case "$*" in
  *session-notify.journal*) echo "journal" >> "$MARK"; exit 0 ;;
  *) echo "a2a" >> "$MARK"; exit 4 ;;
esac
"""

def _stub(dirpath, name, body):
    p = dirpath / name
    p.write_text(body)
    p.chmod(0o755)
    return p

def _call(run_tool, *, stub_dir, mark, extra_env, lib=LIB, timeout=60):
    """Source the lib and call ``oc_notify_session`` once, in a child shell.

    The lib is sourced rather than executed because the exit contract lives in
    the FUNCTION; the CLI wrapper at the bottom of the file is a different entry
    point with its own rc mapping.
    """
    script = (
        'export MARK PATH="%s:$PATH"\n'
        '. "%s"\n'
        't0="$(date +%%s)"\n'
        'oc_notify_session "%s" ops test-runner %s t x\n'
        'rc=$?\n'
        't1="$(date +%%s)"\n'
        'printf "elapsed=%%s rc=%%s\\n" "$((t1-t0))" "$rc"\n'
        % (stub_dir, lib, stub_dir / "bin", UUID)
    )
    env = dict(extra_env)
    return run_tool(["bash", "-c", script], timeout=timeout, env=env)

def _parse(res):
    """``elapsed=<n> rc=<n>`` -> (elapsed, rc), or (None, None) if malformed."""
    elapsed = rc = None
    for tok in res.out.split():
        if tok.startswith("elapsed="):
            elapsed = tok.split("=", 1)[1]
        elif tok.startswith("rc="):
            rc = tok.split("=", 1)[1]
    return elapsed, rc

# =============================================================================
# §57 — the CLI leg needs a budget of its OWN (#466)
# =============================================================================
@pytest.fixture
def hang_dir(scratch):
    d = scratch.path / "nf57"
    d.mkdir(parents=True, exist_ok=True)
    _stub(d, "bin", HANGING_BIN)
    _stub(d, "python3", A2A_ONLY)
    mark = d / "mark"
    mark.write_text("")
    return cf.Node(d, mark=mark)

def test_cli_leg_is_bounded_and_the_fallback_is_reachable(hang_dir, run_tool):
    """#466: a 30 s hang under a 2 s budget must cost ~2 s, not 30.

    Pre-fix this leg had no bound at all, so the outer ``timeout 20`` in the
    shell harness was the only ceiling — and it fired *before* the A2A fallback
    could run, which is precisely the state the fallback existed to cover.
    """
    res = _call(run_tool, stub_dir=hang_dir, mark=hang_dir.mark,
                extra_env={"MARK": str(hang_dir.mark),
                           "OC_NOTIFY_CLI_TIMEOUT": "2"})
    elapsed, rc = _parse(res)
    assert elapsed is not None and rc is not None, \
        "the call produced no parseable result: %r" % res.combined[-400:]
    assert int(elapsed) <= 15, \
        ("the notify CLI leg is UNBOUNDED: took %ss against a 30 s hang with a "
         "2 s budget (#466 regression)" % elapsed)

    mark = hang_dir.mark.read_text()
    assert "invoked" in mark, "the CLI leg never reached the bin stub"
    assert "a2a" in mark, \
        ("the A2A fallback was NOT reached after a hung CLI — the fallback is "
         "still unreachable by construction (#466)")

def test_hung_cli_keeps_the_ambiguous_rc124(hang_dir, run_tool):
    """124 is not a delivery verdict and must never be mapped to one.

    0/2/3 would read downstream as delivered / no_route / refused_in_flight, so
    a timeout must survive the fallback and come back out unchanged.
    """
    res = _call(run_tool, stub_dir=hang_dir, mark=hang_dir.mark,
                extra_env={"MARK": str(hang_dir.mark),
                           "OC_NOTIFY_CLI_TIMEOUT": "2"})
    _, rc = _parse(res)
    assert rc == "124", \
        ("a hung CLI returned rc=%r, want 124 (0/2/3 would read as a delivery "
         "outcome)\n%s" % (rc, res.combined[-400:]))

# =============================================================================
# §58 — per-send sender; the journal fallback stays deleted (#472, #18)
# =============================================================================
@pytest.fixture
def sender_dir(scratch):
    """A refusing bin, the journal-aware python3 seam, and a MATCHING journal row.

    The row is the discriminating input: it matches the target on every field,
    which is exactly what the deleted fallback used to settle a send with.
    """
    d = scratch.path / "nf58"
    d.mkdir(parents=True, exist_ok=True)
    _stub(d, "bin", '#!/bin/sh\necho "argv=$*" >> "$MARK"\nexit 4\n')
    _stub(d, "python3", A2A_WITH_JOURNAL_ARM)

    home = d / "home"
    logs = home / ".opencrabs" / "profiles" / "ops" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "session-notify.journal").write_text(
        "2026-01-01T00:00:00.000000+00:00\tcaller=a2a:seed\ttarget=%s\t"
        "outcome=delivered\texit=0\n" % UUID)

    mark = d / "mark"
    mark.write_text("")
    return cf.Node(d, mark=mark, home=home)

def _sender_call(run_tool, sender_dir, sender):
    env = {"MARK": str(sender_dir.mark),
           "HOME": str(sender_dir.home),
           "OC_NOTIFY_CLI_TIMEOUT": "2"}
    if sender:
        env["OC_NOTIFY_SENDER"] = sender
    return _call(run_tool, stub_dir=sender_dir, mark=sender_dir.mark,
                 extra_env=env)

def test_sender_override_reaches_the_cli(sender_dir, run_tool):
    """#472: the caller's per-SEND label must arrive as ``--sender``.

    Without it the journal's ``caller=a2a:<label>`` is the CALLER's own $3, so
    two sends from one caller are indistinguishable and a neighbour's row can
    settle a send that never landed.
    """
    res = _sender_call(run_tool, sender_dir, "oc-issue-dispatch/#472-abc")
    mark = sender_dir.mark.read_text()
    assert "--sender oc-issue-dispatch/#472-abc" in mark, \
        ("OC_NOTIFY_SENDER did NOT reach the CLI as --sender: mark=%r\n%s"
         % (mark, res.combined[-400:]))

def test_transport_rc_passes_through_with_and_without_a_sender(sender_dir, run_tool):
    """#18: a matching journal row must no longer settle the send.

    Both spellings return the transport's 4. Pre-#18 the row was the fallback's
    whole purpose, so a return of 0 here means the deleted fallback came back.
    """
    with_sender = _sender_call(run_tool, sender_dir, "oc-issue-dispatch/#472-abc")
    sender_dir.mark.write_text("")
    without = _sender_call(run_tool, sender_dir, "")

    _, rc_a = _parse(with_sender)
    _, rc_b = _parse(without)
    assert rc_a == "4" and rc_b == "4", \
        ("rc drifted: override=%r legacy=%r, want 4/4 — a deleted fallback came "
         "back?\n%s\n%s" % (rc_a, rc_b, with_sender.combined[-300:],
                            without.combined[-300:]))

def test_the_lib_never_inspects_the_journal(sender_dir, run_tool):
    """The journal arm must never be entered, in either spelling.

    The ``python3`` stub records WHICH python leg ran, so "the lib inspected the
    journal" stays observable even though the code path is deleted.
    """
    _sender_call(run_tool, sender_dir, "oc-issue-dispatch/#472-abc")
    mark_a = sender_dir.mark.read_text()
    sender_dir.mark.write_text("")
    _sender_call(run_tool, sender_dir, "")
    mark_b = sender_dir.mark.read_text()

    assert "journal" not in mark_a and "journal" not in mark_b, \
        ("the lib STILL inspects the journal (#18 regression): with-sender=%r "
         "legacy=%r" % (mark_a, mark_b))

def test_the_lib_source_names_no_journal_path():
    """The shape guard: a re-introduced journal read reddens here.

    A behavioural leg can only catch a path that RUNS; this one catches the code
    coming back at all, which is what makes the deletion durable.
    """
    assert "session-notify.journal" not in LIB.read_text(), \
        "lib/oc-notify.sh names the journal file again (#18 shape guard)"
