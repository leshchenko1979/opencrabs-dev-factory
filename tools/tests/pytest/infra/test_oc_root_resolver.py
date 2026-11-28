"""``lib/oc-root.sh`` resolver coherence (F-L1/F-L2).

THE SUBJECT IS A PROPERTY, NOT A SCRIPT
    The shell section builds one synthetic tree, mutates it three ways and runs
    three checks. That construction is a hand-rolled property test: *for any
    layout of a tools tree, the resolver names the root the tool actually lives
    in, and the helper and the bootstrap agree on the answer.* So this port
    states the property and drives it over a MATRIX of layouts (depth x
    invocation shape x marker fidelity) instead of transliterating the three
    mutations. The shell's three literal arms survive as named legs below, so a
    regression the property matrix might not have sampled still reddens.

WHAT THE RESOLVER IS FOR (tools/lib/oc-root.sh)
    ``tools/`` is grouped by KIND — ``ship/oc-build``, ``state/oc-ledger`` — so
    ``dirname "$0"`` names the group, not the tools root, and every sibling
    reach (``$OC_TOOLS_DIR/lib/oc-log.sh``) breaks. The bootstrap walks UP to
    the first ancestor holding ``lib/oc-root.sh``, with three arms that are each
    load-bearing, each defending a distinct defect:

      F-L1  the marker must be a REAL ``lib/``. A ``/tmp/lib`` symlink to the
            real ``tools/lib`` makes a marker test that follows symlinks stop
            the walk at ``/tmp`` for EVERY script under ``/tmp`` and resolve
            ``OC_TOOLS_DIR=/tmp`` — rc 127 on every sibling reach, which reads
            as a broken tool.
      basename arm  a marker-less ``tools/`` must STOP the walk. Without it a
            stale tools/ keeps walking and adopts an ANCESTOR's marker — a root
            above the tree the tool lives in.
      F-L2  the documented bootstrap in the file's USAGE block drifted from the
            callers: it showed a 3-line form missing BOTH basename arms while 40
            of 42 callers ran the 4-line form. Prose cannot drift from its
            callers without reddening here.

    Plus one property the shell does not assert and the code comment calls out
    as ``H-2``: ``dirname(".")`` is ``"."``, so a walk given a BARE relative
    name parks on ``"."`` forever. The helper carries a progress break for it;
    ``test_helper_terminates_on_an_unresolvable_path`` pins that it terminates.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

import conftest as cf

ROOT_SH = cf.TOOLS_DIR / "lib" / "oc-root.sh"

# The three LOGIC lines, matched BY PATTERN exactly as the shell leg does
# (``grep -E '^(_oc_r=|if \[ "\$\(basename|if \[ -f "\$_oc_r)'``). Extracting by
# pattern, never by line number, is what makes drift in either file move the
# comparison with it instead of silently comparing nothing.
LOGIC_RE = re.compile(
    r'^(_oc_r=|if \[ "\$\(basename|if \[ -f "\$_oc_r)')

# The walk-up marker the static fleet arm keys on (the entry-preamble module
# uses the same literal, so the two cannot disagree about what "carries the
# walk-up" means).
WALKUP = 'while [ "$_oc_r" != "/" ]'
FIXPOINT_BREAK = '[ "$_oc_r" != "." ]'

# A sweep that matched no files would report zero violations and pass
# vacuously. 49 tools carry the bootstrap; the floor sits below that so ordinary
# churn does not redden while a broken enumerator does.
CARRIER_FLOOR = 40


# =============================================================================
# building a synthetic tools tree
# =============================================================================
def _bootstrap_lines() -> list[str]:
    """The documented bootstrap, extracted from lib/oc-root.sh by pattern."""
    text = ROOT_SH.read_text(encoding="utf-8", errors="replace")
    assert "# USAGE" in text, "lib/oc-root.sh lost its `# USAGE` block"
    seg = text.split("# USAGE", 1)[1].split("#   TOOLS_DIR=", 1)[0]
    out = []
    for raw in seg.splitlines():
        line = raw[4:] if raw.startswith("#   ") else raw
        if LOGIC_RE.match(line):
            out.append(line)
    assert len(out) == 3, (
        "the documented bootstrap yielded %d logic line(s), expected 3 — the "
        "USAGE block or the extraction pattern moved:\n%s" % (len(out), "\n".join(out)))
    return out


def _write_probe(dest, lines: list[str] | None = None):
    """A script whose ONLY job is to print the root the bootstrap resolved."""
    lines = lines or _bootstrap_lines()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "#!/usr/bin/env bash\n" + "\n".join(lines)
        + '\nprintf "%s\\n" "$OC_TOOLS_DIR"\n')
    dest.chmod(0o755)
    return dest


def _plant_root(root, *, real_lib=True):
    """Plant ``<root>/lib/oc-root.sh`` — the marker the walk stops at."""
    lib = root / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "oc-root.sh").write_text(
        ROOT_SH.read_text(encoding="utf-8", errors="replace"))
    # A sibling the bootstrap's own success path can source; its presence keeps
    # the fixture honest about what a real tools/lib looks like.
    (lib / "oc-notify.sh").write_text("")
    return lib


def _make_tree(base, depth, *, lib_kind="real"):
    """A tools tree with a probe at ``depth`` levels of grouping below the root.

    ``depth=0`` is a top-level tool, ``depth=3`` is
    ``tools/ship/deep/deeper/oc-probe`` — the shapes the regroup produced.
    """
    root = base / "tools"
    root.mkdir(parents=True, exist_ok=True)
    if lib_kind == "real":
        _plant_root(root)
    elif lib_kind == "symlink":
        # A BORROWED lib/: the F-L1 defect. Points at the real tree's lib.
        root.mkdir(parents=True, exist_ok=True)
        (root / "lib").symlink_to(ROOT_SH.parent)
    elif lib_kind == "markerless":
        (root / "lib").mkdir(parents=True, exist_ok=True)
        (root / "lib" / "oc-notify.sh").write_text("")
    else:                                        # pragma: no cover - typo guard
        raise ValueError(lib_kind)
    parts = ["g%d" % i for i in range(depth)]
    probe = root.joinpath(*parts) / "oc-probe" if parts else root / "oc-probe"
    _write_probe(probe)
    return root, probe


def _bootstrap_says(run_tool, probe, *, cwd=None, timeout=60):
    res = run_tool([str(probe) if cwd is None else os.path.join(".", probe.name)],
                   timeout=timeout, cwd=cwd)
    return res


def _helper_says(run_tool, script_path, *, timeout=60, cwd=None):
    """``oc_tools_dir <path>`` from a shell that sourced the real lib.

    ``cwd`` is forwarded because a RELATIVE argument is resolved against it:
    ``readlink -f`` happily canonicalises a bare name whose last component does
    not exist, so the walk starts in the CALLER's directory. A leg asserting
    that a relative path is unresolvable must therefore choose the directory,
    or the ambient tree answers for it.
    """
    script = '. "$1" 2>/dev/null; shift; oc_tools_dir "$1"'
    res = run_tool(["/bin/bash", "-c", script, "_", str(ROOT_SH), str(script_path)],
                   timeout=timeout, cwd=cwd)
    return res


# =============================================================================
# F-L2 — the documented bootstrap must equal a real caller's, byte for byte
# =============================================================================
def test_documented_bootstrap_equals_a_real_callers():
    """§77 leg 1: the USAGE block and ``ship/oc-build`` agree on all 3 lines.

    Both sides are extracted by PATTERN, so drift in either file moves the
    comparison rather than silently comparing nothing. The trailing
    ``TOOLS_DIR=`` assignment is deliberately NOT compared byte-for-byte:
    tools annotate it with their own comment (oc-build carries a Duty-6 note),
    and that is not the arm set F-L2 is about.
    """
    doc = _bootstrap_lines()
    caller_text = (cf.TOOLS_DIR / "ship" / "oc-build").read_text(
        encoding="utf-8", errors="replace")
    caller = [l for l in caller_text.splitlines() if LOGIC_RE.match(l)][:3]
    assert len(caller) == 3, "oc-build carries %d logic line(s), expected 3" % len(caller)
    assert doc == caller, (
        "the documented bootstrap DIVERGES from a real caller (F-L2 is back):\n"
        "--- doc\n%s\n--- caller\n%s" % ("\n".join(doc), "\n".join(caller)))


def test_every_bootstrap_carrier_agrees_with_the_documented_form():
    """PROPERTY beyond the shell leg: ALL carriers, not just oc-build.

    F-L2's defect was that prose drifted from 40 of 42 callers while the battery
    compared it against ONE. A single-caller comparison cannot see a second
    divergent form, so this leg sweeps the population. It is the reason the
    defect class is closed rather than the instance.
    """
    doc = _bootstrap_lines()
    divergent = []
    carriers = 0
    for path in sorted(cf.TOOLS_DIR.rglob("oc-*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix in (".py", ".mjs", ".json", ".md", ".log", ".bak", ".pyc"):
            continue
        if ".bak-" in path.name or ".pre-" in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if '^_oc_r="$(cd' not in text and '_oc_r="$(cd' not in text:
            continue
        lines = [l for l in text.splitlines() if LOGIC_RE.match(l)][:3]
        if not lines:
            continue
        carriers += 1
        if lines != doc:
            divergent.append("%s: %r" % (path.relative_to(cf.TOOLS_DIR), lines))
    assert carriers >= CARRIER_FLOOR, (
        "enumerated only %d bootstrap carrier(s) (floor %d) — the sweep is not "
        "seeing the fleet" % (carriers, CARRIER_FLOOR))
    assert not divergent, (
        "%d carrier(s) diverge from the documented bootstrap:\n  %s"
        % (len(divergent), "\n  ".join(divergent[:5])))


# =============================================================================
# F-L1 population — no carrier may read bare $TOOLS_DIR before assigning it
# =============================================================================
def _population_sweep(root):
    """The resolver exports OC_TOOLS_DIR, NOT TOOLS_DIR (the shell leg's rule).

    A tool that READS the bare name without assigning it dies ``rc 127`` under
    ``set -u`` — silently if the read precedes ``set -u``, fatally after. Order
    matters: an assignment BELOW the first bare read still crashes.
    """
    boot = re.compile(r'^_oc_r="\$\(cd', re.M)
    bare = re.compile(r'(?<![_A-Za-z])TOOLS_DIR')
    assign = re.compile(r'^[ \t]*(?:export[ \t]+)?TOOLS_DIR=')
    skip = (".py", ".mjs", ".json", ".md", ".log", ".bak", ".pyc")
    carriers, bad = 0, []
    for dp, dns, fns in os.walk(str(root)):
        dns[:] = [d for d in dns if d not in (".git", "__pycache__")]
        for fn in fns:
            if fn.endswith(skip):
                continue
            p = os.path.join(dp, fn)
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if not boot.search(txt):
                continue
            carriers += 1
            lines = txt.splitlines()
            first_assign = next(
                (i for i, l in enumerate(lines) if assign.match(l)), None)
            early = 0
            for i, line in enumerate(lines):
                if line.lstrip().startswith("#"):
                    continue
                if not bare.findall(line.replace("OC_TOOLS_DIR", "")):
                    continue
                if first_assign is None or i < first_assign:
                    early += 1
            if early:
                why = ("no assignment" if first_assign is None
                       else "read before assignment")
                bad.append("%s (%d bare read(s), %s)"
                           % (os.path.relpath(p, str(root)), early, why))
    return carriers, bad


def test_no_carrier_reads_bare_tools_dir_unassigned():
    """§77 leg 2 (population arm) — the assertion is on the POPULATION.

    Asserting on ONE reference caller was the defect, not the assertion: a lane
    copying the documented form inherited an unset variable and this leg could
    not see it. The ``carriers`` floor is a POSITIVE CONTROL — a sweep that
    matched nothing would report zero violations and pass vacuously.
    """
    carriers, bad = _population_sweep(cf.TOOLS_DIR)
    assert carriers >= CARRIER_FLOOR, (
        "swept only %d carrier(s) (floor %d)" % (carriers, CARRIER_FLOOR))
    assert not bad, (
        "%d carrier(s) read bare $TOOLS_DIR with no assignment (swept %d):\n  %s"
        % (len(bad), carriers, "\n  ".join(bad[:8])))


# =============================================================================
# F-L1 arms A/B and the basename arm — the shell's three literal legs
# =============================================================================
def test_real_lib_resolves_to_the_tools_root(tmp_path, run_tool):
    """§77 arm A (control): a REAL lib/ must still resolve, or the F-L1 guard
    broke the normal path and every sibling reach with it."""
    root, probe = _make_tree(tmp_path, 1)
    res = _helper_says(run_tool, probe)
    assert res.rc == 0, "oc_tools_dir rc=%s\n%s" % (res.rc, res.combined[-600:])
    assert res.out.strip() == str(root), (
        "oc_tools_dir resolved %r, want %r" % (res.out.strip(), str(root)))


def test_symlinked_lib_is_rejected(tmp_path, run_tool):
    """§77 arm B (the F-L1 defect): a SYMLINKED lib/ is a BORROWED lib/, so that
    ancestor is not our root. Pre-fix this returned the fixture root."""
    root, probe = _make_tree(tmp_path, 1, lib_kind="symlink")
    res = _helper_says(run_tool, probe)
    assert res.rc != 0 and res.out.strip() != str(root), (
        "oc_tools_dir ACCEPTED a symlinked lib/ and adopted %r — the F-L1 defect "
        "is back" % res.out.strip())


def test_symlinked_lib_under_a_tools_dir_diverges_by_design(tmp_path, run_tool):
    """CROSS-CHECK the shell does not make: both implementations, one fixture.

    F-L1's stated cost was that the helper and the bootstrap "resolve the same
    question by different rules ... and the divergence will be found by whoever
    is debugging a sibling reach at 3am". The shell pins each side SEPARATELY;
    this leg pins them TOGETHER, on the one shape where they legitimately differ:

      helper      refuses outright (rc 1). It has no fallback, and a borrowed
                  lib/ is not a marker, so there is no root to name.
      bootstrap   names the tools dir ANYWAY, through the ``basename == tools``
                  arm — and, importantly, it does NOT source the borrowed lib
                  (the ``[ ! -L ]`` guard sends it down the else branch).

    Both are defensible and they are NOT the same rule, which is precisely the
    hazard F-L1 named. Recording it here means a future change to either side
    shows up as a changed verdict rather than as a surprise at a sibling reach.
    """
    root, probe = _make_tree(tmp_path, 1, lib_kind="symlink")
    helper = _helper_says(run_tool, probe)
    boot = _bootstrap_says(run_tool, probe)
    assert helper.rc != 0 and helper.out.strip() == "", (
        "helper resolved %r (rc=%s) on a borrowed lib/ — F-L1 arm B regressed"
        % (helper.out.strip(), helper.rc))
    assert boot.out.strip() == str(root), (
        "the bootstrap resolved %r, expected the tools dir %r via the "
        "basename arm (the borrowed lib must not be SOURCED, but the nearest "
        "dir named `tools` is still the root)" % (boot.out.strip(), str(root)))


def test_markerless_tools_stops_the_walk(tmp_path, run_tool):
    """§77 basename arm: a marker-less tools/ must STOP the walk rather than let
    it adopt an ancestor's marker as its root.

    Without the arm the helper returns ``$ANC`` — a root ABOVE the tree the tool
    actually lives in.
    """
    anc = tmp_path / "anc"
    _plant_root(anc)                      # a real marker ABOVE the tree
    tools = anc / "tools"
    (tools / "sub").mkdir(parents=True)
    probe = _write_probe(tools / "sub" / "oc-probe")
    res = _helper_says(run_tool, probe)
    assert res.out.strip() != str(anc), (
        "oc_tools_dir adopted the ANCESTOR root %r across a marker-less tools/ — "
        "the basename arm is missing" % str(anc))
    # The bootstrap has its OWN fallback (case 2: no root above -> the script's
    # dir). It must name the marker-less tools/, never the ancestor above it.
    boot = _bootstrap_says(run_tool, probe)
    assert boot.out.strip() != str(anc), (
        "the bootstrap adopted the ancestor %r across a marker-less tools/"
        % str(anc))


# =============================================================================
# THE PROPERTY — convergence over depth x invocation shape
# =============================================================================
@pytest.mark.parametrize("depth", [0, 1, 2, 3, 4])
def test_bootstrap_converges_on_the_tools_root_at_any_depth(tmp_path, run_tool, depth):
    """PROPERTY: for every grouping depth, the bootstrap names the tools root.

    This is the assertion the whole file exists for, stated as a property: a
    tool moved from ``tools/oc-x`` to ``tools/ship/deep/deeper/oc-x`` must
    resolve the SAME root. The shell's own construction samples one depth; the
    regroup that motivated the resolver produced several.
    """
    root, probe = _make_tree(tmp_path, depth)
    res = _bootstrap_says(run_tool, probe)
    assert res.rc == 0, "probe rc=%s\n%s" % (res.rc, res.combined[-600:])
    assert res.out.strip() == str(root), (
        "depth=%d resolved %r, want %r" % (depth, res.out.strip(), str(root)))


@pytest.mark.parametrize("depth", [0, 1, 2, 3, 4])
def test_helper_and_bootstrap_agree_at_any_depth(tmp_path, run_tool, depth):
    """PROPERTY: the helper and the bootstrap are two implementations of ONE
    question, and a disagreement is found at 3am by whoever is debugging a
    sibling reach. This is the invariant F-L1 was a violation of."""
    root, probe = _make_tree(tmp_path, depth)
    boot = _bootstrap_says(run_tool, probe)
    helper = _helper_says(run_tool, probe)
    assert helper.rc == 0, (
        "depth=%d: oc_tools_dir rc=%s\n%s" % (depth, helper.rc, helper.combined[-400:]))
    assert helper.out.strip() == boot.out.strip(), (
        "depth=%d: helper says %r, bootstrap says %r — they resolve the same "
        "question by different rules" % (depth, helper.out.strip(), boot.out.strip()))


@pytest.mark.parametrize("shape", ["absolute", "dot-slash", "parent-relative", "shim"])
def test_relative_invocation_resolves_the_same_root(tmp_path, run_tool, shape):
    """PROPERTY: the root does not depend on HOW the tool was invoked.

    ``./oc-probe`` from its own directory is the invocation that broke #708 for
    the *entry preamble*; the resolver must be immune to it too, because
    ``cd "$(dirname "$0")"`` yields ``.`` for a bare ``./name`` and a walk that
    starts at ``.`` must still climb to a real root. ``shim`` adds the symlink
    case the lib's own comment pins: a shim converges on the same root either
    way.
    """
    root, probe = _make_tree(tmp_path, 2)
    if shape == "absolute":
        res = run_tool([str(probe)], timeout=60)
    elif shape == "dot-slash":
        res = run_tool(["./" + probe.name], timeout=60, cwd=probe.parent)
    elif shape == "parent-relative":
        child = probe.parent / "sub"
        child.mkdir()
        res = run_tool(["../" + probe.name], timeout=60, cwd=child)
    else:  # shim
        shim = root / "oc-shim"
        shim.symlink_to(probe)
        res = run_tool([str(shim)], timeout=60)
    assert res.rc == 0, "%s: rc=%s\n%s" % (shape, res.rc, res.combined[-600:])
    assert res.out.strip() == str(root), (
        "%s invocation resolved %r, want %r" % (shape, res.out.strip(), str(root)))


# =============================================================================
# the fallback arm — a fixture copy must NOT escape to the real tree
# =============================================================================
def test_fallback_is_the_scripts_own_dir_when_no_root_exists(tmp_path, run_tool):
    """Case 2 of the resolver: NO tools root above the script.

    This is load-bearing for the battery itself: many selftests copy a tool into
    a temp dir beside FAKE siblings and assert the tool uses THOSE. A walk that
    escaped to the real tools/ would silently defeat the test's isolation —
    oc-ship's journal legs then read rc 127 against the real tree.
    """
    lone = tmp_path / "lone" / "a" / "b"
    probe = _write_probe(lone / "oc-probe")
    res = _bootstrap_says(run_tool, probe)
    assert res.rc == 0, "probe rc=%s\n%s" % (res.rc, res.combined[-600:])
    assert res.out.strip() == str(lone), (
        "fallback resolved %r, want the script's own dir %r — a walk escaped the "
        "fixture" % (res.out.strip(), str(lone)))


def test_a_bare_lib_without_the_marker_is_not_a_root(tmp_path, run_tool):
    """MARKER FIDELITY: the marker is ``lib/oc-root.sh`` itself, not a bare
    ``lib/``. An unrelated project's lib/ must never be mistaken for ours."""
    outer = tmp_path / "outer"
    _plant_root(outer)                       # the REAL root, two levels up
    inner = outer / "vendor" / "proj"
    (inner / "lib").mkdir(parents=True)
    (inner / "lib" / "unrelated.sh").write_text("")
    probe = _write_probe(inner / "oc-probe")
    res = _bootstrap_says(run_tool, probe)
    assert res.out.strip() == str(outer), (
        "a bare lib/ without oc-root.sh was treated as a root: resolved %r, "
        "want %r" % (res.out.strip(), str(outer)))


# =============================================================================
# H-2 — the walk must TERMINATE on an unresolvable path
# =============================================================================
@pytest.mark.parametrize("arg", ["nodir/oc-x", "bare-name", "."])
def test_helper_terminates_on_an_unresolvable_path(tmp_path, run_tool, arg):
    """``dirname(".")`` is ``"."`` — a walk that starts there never advances.

    The helper carries a progress break (``[ "$_ocd" = "$_ocp" ] && break``).
    Without it this call SPINS FOREVER at 100% CPU with no output, which is
    exactly the #708 shape one layer down. The bound is the assertion: a hang
    reports rc 124 here instead of wedging the suite.

    The cwd is a THROWAWAY dir, and that is load-bearing rather than tidiness:
    every arg here is relative, and ``readlink -f`` canonicalises a bare name
    whose last component is missing. Run from inside this repo the walk starts
    in the real tree and correctly finds the real ``tools/`` — the helper is
    right and the leg is asking the wrong question. From an empty dir there is
    no marker above the start, so rc 1 means exactly "this path resolves
    nowhere", which is what H-2 is about.
    """
    res = _helper_says(run_tool, arg, timeout=20, cwd=tmp_path)
    assert not res.timed_out, (
        "oc_tools_dir %r SPUN (killed at 20s) — the progress break is gone"
        % arg)
    assert res.rc != 0, (
        "oc_tools_dir %r returned 0 with %r; an unresolvable path must FAIL, "
        "not resolve to something" % (arg, res.out.strip()))


def test_without_the_progress_break_the_helper_spins(tmp_path, run_tool):
    """NEGATIVE CONTROL for the leg above — the break must be the thing that saves it.

    The same helper with the ``H-2`` progress break DELETED must still be
    spinning when the bound fires. Without this, ``test_helper_terminates_...``
    could pass because the path happens to be unresolvable for an unrelated
    reason, and a re-introduced fixpoint would go unnoticed.
    """
    text = ROOT_SH.read_text(encoding="utf-8", errors="replace")
    kept = [l for l in text.splitlines() if '"$_ocd" = "$_ocp"' not in l]
    assert len(kept) < len(text.splitlines()), (
        "the H-2 progress break is GONE from lib/oc-root.sh — the helper now "
        "spins on a bare relative name (this leg would otherwise pass vacuously)")
    mutant = tmp_path / "oc-root-nobreak.sh"
    mutant.write_text("\n".join(kept))
    res = run_tool(["/bin/bash", "-c",
                    '. "$1" 2>/dev/null; shift; oc_tools_dir "$1"', "_",
                    str(mutant), "nodir/oc-x"], timeout=6)
    assert res.timed_out, (
        "the break-less mutant returned rc=%s instead of spinning — either the "
        "walk now advances another way, or this control no longer reproduces "
        "the fixpoint" % res.rc)


# =============================================================================
# the static fleet invariant shared with §84
# =============================================================================
def test_every_walkup_carrier_has_the_fixpoint_break():
    """Every file that still walks up must carry the ``.`` break.

    Keyed on the BREAK's presence, never on the old line's absence, so this leg
    asserts the fix rather than merely failing to find the bug. (The behavioural
    half of #708 lives in ``test_entry_preamble.py``.)
    """
    carriers, missing = 0, []
    for path in sorted(cf.TOOLS_DIR.rglob("oc-*")):
        if not path.is_file() or path.is_symlink():
            continue
        if "/archive/" in str(path) or ".bak" in path.name or ".pre-" in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if WALKUP not in text:
            continue
        carriers += 1
        if FIXPOINT_BREAK not in text:
            missing.append(str(path.relative_to(cf.TOOLS_DIR)))
    assert carriers >= CARRIER_FLOOR, (
        "walk-up enumerated only %d file(s) (floor %d) — the glob is not seeing "
        "the fleet" % (carriers, CARRIER_FLOOR))
    assert not missing, (
        "%d file(s) walk up WITHOUT the fixpoint break (#708): %s"
        % (len(missing), ", ".join(missing[:6])))


# =============================================================================
# NEGATIVE CONTROL — the property matrix must be able to FAIL
# =============================================================================
@pytest.mark.parametrize("depth,converges", [(0, True), (1, False), (3, False)])
def test_the_property_matrix_discriminates(tmp_path, run_tool, depth, converges):
    """CONTROL: a ``dirname "$0"`` bootstrap (the pre-resolver form) is exactly
    right at depth 0 and wrong at every depth below it.

    Without this leg the matrix above could be passing on a property that any
    implementation satisfies — the battery's own idiom is that a check which
    cannot fire is decoration. Here the SAME assertion runs against the KNOWN
    BROKEN form and must invert.
    """
    root, probe = _make_tree(tmp_path, depth)
    broken = ['_oc_r="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || _oc_r="."',
              'OC_TOOLS_DIR="$_oc_r"']
    _write_probe(probe, broken)
    res = run_tool([str(probe)], timeout=60)
    assert res.rc == 0, res.combined[-400:]
    got = res.out.strip()
    if converges:
        assert got == str(root), (
            "the broken form resolved %r at depth 0; it should be right THERE — "
            "otherwise this control is measuring something else" % got)
    else:
        assert got != str(root), (
            "the broken dirname-only form resolved the root at depth %d — the "
            "property matrix cannot be discriminating" % depth)
