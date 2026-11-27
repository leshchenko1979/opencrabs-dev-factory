"""SIGKILL evidence: the dispatch narrative must SURVIVE a kill mid-send (#451).

WHAT THIS PORTS
    ``run.sh`` section 61 (``section "oc-issue-dispatch SIGKILL evidence
    (#451)"``) — the post-fix cell and its DERIVED control.

THE DEFECT
    ``oc-issue-dispatch`` builds its narrative on stdout, then sends. Killed
    mid-send, an UNBUFFERED narrative is lost with the process, so the operator
    finds an empty log and a dead run — no record of what it was doing or why.
    The fix makes the narrative durable before the send.

WHY THE CONTROL IS DERIVED, NOT WRITTEN
    A leg that only asserts "the post-fix run left bytes" passes if the tool
    happens to be chatty. So the control is the SAME tool with its line-buffering
    mechanism INVERTED — one ``sed`` over the single ``line_buffering=True``
    site, asserted to hit exactly one line. Two cells, same timeout, same stub:
    post-fix must leave evidence, the control must leave NONE. A single-sided
    check cannot tell "durable" from "verbose".

WHY THE KILL IS TRIGGERED BY A SENTINEL, NOT BY A WALL CLOCK
    ``run.sh`` bounds the cell with ``timeout -s KILL 10``. A wall bound does not
    say WHERE the kill lands: it reproduces #451 only when the process reaches the
    send inside 10 s. Under ``-n 2`` the machine is busier, the tool reaches the
    send later, and the kill lands BEFORE the narrative is printed — the post-fix
    cell then reads 0 B and the pair stops discriminating (measured: this leg
    failed at ``-n 2`` while passing serially, with both cells at 0 B). The bound
    was measuring the box's load, not the tool's behaviour.

    So the notify stub drops a sentinel and the harness kills the process group
    the moment it appears. The kill is now INSIDE the send by construction, and
    the leg's precondition (rc 137 with the narrative already durable) is an
    observation rather than a hope. The wall bound survives only as a backstop
    for a cell that never reaches the send at all.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

from lib import harness as H

pytestmark = [
    pytest.mark.serial,
    pytest.mark.xdist_group("battery-sigkill"),
]

# The send must BLOCK so the kill lands inside it. A real notify would reach the
# live bus or return instantly, and neither reproduces #451. The sentinel is
# written FIRST, so its appearance proves the process reached the send; the
# harness kills on that signal instead of guessing with a wall clock.
NOTIFY_STUB = "#!/bin/sh\n: > \"$OC_D451_SENTINEL\"\nsleep 30\n"

# Backstop only: a cell that never reaches the send is a broken fixture, not a
# #451 observation, so it must fail rather than hang. Never the trigger.
KILL_BACKSTOP_SECONDS = 120
SENTINEL_TIMEOUT_SECONDS = 60

# gh is stubbed because whether the fork has an open issue #451 is a HOST fact,
# not a property of this code. The LIST stays empty on purpose: the send must be
# reached through the DIRECT lookup, which is the path #483 added. A stub that
# answered "[]" to the single-issue lookup too would model a genuinely missing
# issue, and the run would exit 1 BEFORE the send.
GH_STUB = """#!/bin/sh
case "$1 $2" in
  "issue view") echo '{"number":451,"title":"fix(tools): oc-issue-dispatch hangs","body":"the culprit is tools/issue/oc-issue-dispatch","labels":[{"name":"tools"}],"state":"OPEN","stateReason":null}' ;;
  *) echo "[]" ;;
esac
"""

KILL_SECONDS = 10

def derive_control(src: str) -> str:
    """The DERIVED control: invert the line-buffering mechanism at its ONE site.

    A module-level function so the derivation's own invariant is testable BY
    NAME (``test_the_control_derivation_inverts_exactly_one_site``). While it
    lived inline in ``DispatchStub.__init__`` a tool edit that moved or removed
    the ``line_buffering=True`` site surfaced as "3 errors" from fixture setup,
    with the reason buried in a traceback — the assertion was real but it had no
    name to fail under.

    Raises ``AssertionError`` rather than returning a sentinel: a control that
    cannot be derived means the discriminator is unsound, and a leg that skipped
    instead of failing would report the pair as green.
    """
    mutated = src.replace("line_buffering=True", "line_buffering=False")
    assert mutated != src, (
        "the control derivation found no line_buffering=True site — the "
        "#451 discriminator cannot be built against this tool version")
    assert mutated.count("line_buffering=False") == 1, (
        "the control derivation inverted %d line_buffering sites, expected 1 "
        "— the discriminator is unsound"
        % mutated.count("line_buffering=False"))
    return mutated


class DispatchStub:
    """A hermetic copy of the tool tree, its stubs, and the two dispatch cells."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        tools = H.TOOLS_DIR
        self.tools = self.root / "tools"
        for sub in ("lib", "issue", "state", "bin"):
            (self.tools / sub).mkdir(parents=True, exist_ok=True)
        (self.root / "home").mkdir(exist_ok=True)

        shutil.copy2(tools / "issue" / "oc-issue-dispatch",
                     self.tools / "issue" / "oc-issue-dispatch")
        (self.tools / "issue" / "oc-issue-dispatch").chmod(0o755)
        for f in sorted((tools / "lib").glob("*.py")):
            shutil.copy2(f, self.tools / "lib" / f.name)
        # lib/oc-root.sh is the marker the depth-agnostic bootstrap walks up to
        # find. A fixture that copies only *.py leaves the tool unable to resolve
        # the tools root, so TOOL_DIR collapses to the tool's own subdir and the
        # shared lib/ disappears.
        for name in ("oc-root.sh", "oc-log.sh"):
            src = tools / "lib" / name
            if src.is_file():
                shutil.copy2(src, self.tools / "lib" / name)
        # #177: dispatch reads the ledger through oc-ledger. Without the reader
        # (and oc-log.sh, which it sources) the stub exits rc 2 before the notify
        # sleep, so the SIGKILL never lands mid-send.
        shutil.copy2(tools / "state" / "oc-ledger", self.tools / "state" / "oc-ledger")
        (self.tools / "state" / "oc-ledger").chmod(0o755)

        (self.tools / "lib" / "oc-notify.sh").write_text(NOTIFY_STUB, encoding="utf-8")
        (self.tools / "lib" / "oc-notify.sh").chmod(0o755)
        (self.tools / "bin" / "gh").write_text(GH_STUB, encoding="utf-8")
        (self.tools / "bin" / "gh").chmod(0o755)
        (self.root / "ledger.json").write_text(
            '{"workers":[],"events":[]}\n', encoding="utf-8")

        # THE DERIVED CONTROL: invert the line-buffering mechanism at its one
        # site. The invariant is asserted inside derive_control, which also has
        # its own named leg — see test_the_control_derivation_inverts_exactly_one_site.
        src = (tools / "issue" / "oc-issue-dispatch").read_text(encoding="utf-8")
        mutated = derive_control(src)
        self.nolb = self.tools / "oc-issue-dispatch-nolb"
        self.nolb.write_text(mutated, encoding="utf-8")
        self.nolb.chmod(0o755)

    def dispatch(self, script: Path, label: str) -> tuple[int, int, int, bool]:
        """Run one cell; return ``(rc, stdout_bytes, budget_announcements, reached_send)``.

        ``reached_send`` is RETURNED, not just used to decide the kill, because it
        is the precondition the two cells rest on: "killed mid-send" must be an
        OBSERVATION the leg asserts, never an inference from ``rc == 137``. Both
        the sentinel kill and the 120 s backstop produce 137, so rc alone cannot
        tell "the kill landed inside the send" from "the cell hung and was
        backstopped" — the second is a broken fixture, not a #451 observation.

        The cell is killed by a SENTINEL: the notify stub touches
        ``$OC_D451_SENTINEL`` as its first act, and this method kills the process
        group the instant the file appears. That makes "the kill landed inside
        the send" a precondition the fixture ESTABLISHES rather than one it hopes
        for — a wall-clock bound landed before the send under ``-n 2`` and turned
        the pair into two zero-byte cells.

        ``OC_TOOLS_NOLOG`` is re-exported explicitly: ``env -i`` drops the
        battery's own export, and without it these synthetic runs would append to
        the unified tools log — a live-state write from a test.

        ``--allow-landed --redispatch``: this fixture uses issue 451 purely as a
        VEHICLE for the SIGKILL-survival question, and #451's fix IS landed.
        Since #370 the targeted path runs the same eligibility arms as ``--auto``,
        so the fixture must bypass them or it refuses rc 8 before ever reaching
        the notify leg it exists to test.
        """
        out = self.root / ("out-%s.txt" % label)
        err = self.root / ("err-%s.txt" % label)
        sentinel = self.root / ("sentinel-%s" % label)
        sentinel.unlink(missing_ok=True)
        env = {
            "HOME": str(self.root / "home"),
            "PATH": "%s:/usr/bin:/bin" % (self.tools / "bin"),
            "OC_TOOLS_NOLOG": "1",
            "OC_D451_SENTINEL": str(sentinel),
            "OC_DISPATCH_NOTIFY_TIMEOUT": "60",
            "OC_DISPATCH_RECEIPT_GRACE": "5",
        }
        with open(out, "wb") as fo, open(err, "wb") as fe:
            p = subprocess.Popen(
                [str(script), "451",
                 "--to", "deadbeef-0000-0000-0000-000000000000",
                 "--allow-landed", "--redispatch",
                 "--ledger", str(self.root / "ledger.json"),
                 "--repo", str(H.tools_root())],
                stdout=fo, stderr=fe, env=env, cwd=str(self.root),
                start_new_session=True)

            reached_send = False
            deadline = time.monotonic() + SENTINEL_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if sentinel.exists():
                    reached_send = True
                    break
                if p.poll() is not None:
                    break
                time.sleep(0.02)
            if reached_send:
                # SIGKILL the whole group: the dispatch and the notify stub it is
                # blocked in must both die, exactly as #451 describes.
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    p.kill()
            try:
                p.wait(timeout=KILL_BACKSTOP_SECONDS)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    p.kill()
                p.wait(timeout=30)

        data = out.read_bytes()
        # A SIGKILLed child reports the raw wait status (-9). Normalise to the
        # shell convention 128+9=137: that is what run.sh asserts and what the
        # #451 evidence is documented as, so the leg speaks the same language as
        # the thing it ports.
        rc = p.returncode
        if rc < 0:
            rc = 128 - rc
        return (rc, len(data),
                len(re.findall(rb"notify budget", data)),
                reached_send)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


@pytest.fixture
def dispatch(tmp_path):
    d = DispatchStub(tmp_path / "d451")
    yield d
    d.close()

# =============================================================================
# the two cells
# =============================================================================
def test_the_dispatch_narrative_survives_a_sigkill_mid_send(dispatch):
    """POST-FIX: killed mid-send, the narrative is still on disk (#451).

    rc 137 is the precondition, not a nice-to-have: if the kill did not land
    mid-send the leg is not testing SIGKILL survival at all.
    """
    rc, nbytes, announcements, reached_send = dispatch.dispatch(
        dispatch.tools / "issue" / "oc-issue-dispatch", "postfix")
    assert reached_send, (
        "post-fix: the notify stub never dropped its sentinel, so the kill came "
        "from the backstop rather than from INSIDE the send — the cell is not a "
        "#451 observation, it is a hung fixture")
    assert rc == 137, (
        "post-fix: rc=%d, want 137 — the kill did not land mid-send, so this "
        "leg tests nothing (#451 precondition)" % rc)
    assert nbytes > 0 and announcements >= 1, (
        "post-fix: killed run left %dB / %d budget announcements — the evidence "
        "was discarded (#451 regression)" % (nbytes, announcements))

def test_without_line_buffering_the_same_run_leaves_nothing(dispatch):
    """CONTROL: the derived mutant leaves 0 B — so the cell above can FAIL.

    Identical timeout, identical stubs, one inverted mechanism. Without this the
    post-fix assertion could be green because the tool is chatty rather than
    because the narrative is durable.
    """
    rc, nbytes, announcements, reached_send = dispatch.dispatch(
        dispatch.nolb, "prefix")
    assert reached_send, (
        "control: the notify stub never dropped its sentinel, so this cell was "
        "backstopped rather than killed mid-send — it is not comparable to the "
        "post-fix cell")
    assert rc == 137, (
        "control: rc=%d, want 137 — the cells are not comparable (the kill did "
        "not land mid-send in the mutant either)" % rc)
    assert nbytes == 0 and announcements == 0, (
        "control: the unbuffered run left %dB / %d announcements — this cell "
        "cannot fail on the pre-fix artifact, so it proves nothing"
        % (nbytes, announcements))

def test_the_two_cells_are_actually_different_runs(dispatch):
    """A guard on the pair: same kill, DIFFERENT evidence.

    Stated as its own leg because the two above could both pass while the
    discriminator was dead (e.g. both cells accidentally ran the same script).
    This is the assertion that the PAIR discriminates.
    """
    rc_a, bytes_a, _, send_a = dispatch.dispatch(
        dispatch.tools / "issue" / "oc-issue-dispatch", "pair-fix")
    rc_b, bytes_b, _, send_b = dispatch.dispatch(dispatch.nolb, "pair-ctl")
    assert send_a and send_b, (
        "the pair was not killed inside the send on both sides (reached=%s/%s) "
        "— the comparison is between two backstopped runs" % (send_a, send_b))
    assert (rc_a, rc_b) == (137, 137), (
        "the pair did not both die mid-send (rc=%d/%d)" % (rc_a, rc_b))
    assert bytes_a > 0 and bytes_b == 0, (
        "the pair does not discriminate: post-fix left %dB, control left %dB"
        % (bytes_a, bytes_b))

# =============================================================================
# the derivation invariant, BY NAME
# =============================================================================
def test_the_control_derivation_inverts_exactly_one_site():
    """run.sh §61's FIRST assertion: the control is derivable, and sound.

    ``run.sh`` asserts ``grep -c 'line_buffering=False' == 1`` on the derived
    file and calls a miss "the discriminator is unsound". That assertion used to
    live only inside ``DispatchStub.__init__``, where a tool edit that moved or
    removed the site surfaced as three setup ERRORs and the reason had to be dug
    out of a traceback.

    Named here so the fault reports as itself. ``derive_control`` is the SAME
    function the fixture uses, so this leg cannot drift from the construction it
    describes — it is a direct probe of the shipped tool, not a re-implementation.
    """
    src = (H.TOOLS_DIR / "issue" / "oc-issue-dispatch").read_text(encoding="utf-8")
    # Precondition stated separately so a rename reports as a rename, not as an
    # "unsound discriminator" — the two faults want different fixes.
    assert src.count("line_buffering=True") == 1, (
        "the shipped tool carries %d line_buffering=True sites, expected exactly "
        "1 — #451's durability mechanism moved or was duplicated, so the derived "
        "control no longer isolates it" % src.count("line_buffering=True"))
    mutated = derive_control(src)
    assert mutated.count("line_buffering=False") == 1, (
        "the derivation inverted %d sites, expected 1"
        % mutated.count("line_buffering=False"))
    # The mutation must be the ONLY difference: a control that also changed
    # something else would not be a single-variable discriminator.
    assert mutated.replace("line_buffering=False", "line_buffering=True") == src, (
        "the derived control differs from the shipped tool in more than the "
        "line_buffering site — it is not a single-variable mutant")
