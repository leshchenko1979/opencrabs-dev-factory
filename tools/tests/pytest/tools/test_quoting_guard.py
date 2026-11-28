"""Ported: the shell-quoting guard — run.sh §82 (``python3 -c`` / heredoc fences).

THE SUBJECT IS SOURCE TEXT, NOT RUNTIME BEHAVIOUR
    Every other section in this suite drives a tool and reads its exit code.
    This one reads the TEXT of every tool, because the defect it prevents is
    invisible at runtime until it fires in production:

      ARM A  a ``-c`` body opened with a DOUBLE quote — a backtick inside it
             runs command substitution, so the body's own text becomes shell
             input. This cost a real phantom ``harvest: command not found``.
      ARM B  a heredoc feeding ``python3`` whose DELIMITER IS UNQUOTED — ``$VAR``
             and backticks expand inside the body before python ever sees it.
             An unquoted heredoc carrying a doubled triple-quote closes the
             enclosing shell string and destroys the tool that contains it.
      ARM D  an UNESCAPED ``$`` in a ``-c`` body: bash expands it in the Python
             SOURCE (#327 class b), so the program's text is corrupted.
      ARM C  the #323 SYMPTOM: a stray interior ``"`` closes the ``-c`` body
             early and the Python that follows is read as SHELL. ``bash -n`` is
             INTENT-FREE — it reports what the shell reads, never what the author
             meant — so it is the one detector that sees this class.

    The fleet measures 0 sites today, so the section is a CARRIER, not a sweep:
    the first new site reddens here instead of surfacing as a phantom command.

WHY THE CANARIES ARE BUILT BY INTERPOLATION
    This file lives under ``tools/``, so the LIVE scan reads it. A hazard
    written literally here would be found as a REAL site and the leg would
    false-positive against its own fixture — the shell makes the same move
    (``SQ_BT="$(printf '\\140')"``) for the same reason. Every hazard character
    below arrives from ``chr()`` or a constant, so no literal hazard text exists
    in this file. ``test_this_module_is_itself_clean`` pins that property.

STATED BLIND SPOT (inherited, not papered over)
    ``$VAR`` and ``$(cmd)`` inside a DOUBLE-quoted body are not detected by ARM
    A — they cannot be told apart from a shell argument that FOLLOWS the closing
    quote without a full parser, and a rule that guessed would fire on this
    tree's 28 legitimate one-line ``-c`` calls. ARM A therefore keys on the
    BACKTICK, which is unambiguous inside a double-quoted body; ARM D keys on an
    unescaped ``$``. The gap is ``$(...)`` and it is asserted as a KNOWN GAP
    below rather than left for a reader to discover.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

import conftest as cf

BT = chr(96)          # backtick
DQ = chr(34)          # double quote
DOL = "$"

# The ONE interpolation site that SURVIVES the #327 conversion, keyed on
# (normalised path, stripped line) — never on the path alone. Here the PROGRAM
# itself arrives in a shell variable, fully quoted, so no unquoted expansion can
# reach the Python source and `exec` makes it the whole invocation. The body is
# 4 characters, so there is no room for a stray quote to hide in.
_SITE_ALLOW = {
    ("tools/lib/oc_sqlite",
     "exec python3" + " -c " + DQ + "$_PY" + DQ + " " + DQ + "$_DB" + DQ
     + " " + DQ + "$_SQL" + DQ),
}

# A sweep that scanned no files would report zero findings and pass vacuously.
SHELL_TOOL_FLOOR = 40


# =============================================================================
# the scanner — one implementation, arms selectable so a control can blind it
# =============================================================================
def _norm(p: str) -> str:
    """``/abs/.../tools/x`` -> ``tools/x``, so the allowlist is path-stable."""
    p = str(p)
    return ("tools/" + p.split("tools/", 1)[1]) if "tools/" in p else p


def _dquote_body(text: str, start: int):
    """The region bash reads as the ``-c`` body: up to the first UNESCAPED ``"``.

    Reading it the way bash does is the point — a stray interior ``"`` is
    invisible HERE (bash stops at it too), so that failure mode is caught by the
    ``bash -n`` sweep instead, which cannot be fooled by what the author MEANT.
    """
    j = start
    while j < len(text):
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == DQ:
            return text[start:j], j
        j += 1
    return text[start:], len(text)


# The double-quoted `-c` opener, assembled so this module carries no site.
_C_OPEN = "python3" + " -c " + DQ


def scan_text(path, text: str, arms=("A", "B", "D")):
    """Find hazard fences in ``text``. Returns a list of ``(path, message)``."""
    out = []
    if "A" in arms:
        # ARM A: a DOUBLE-quoted -c body carrying a backtick.
        for m in re.finditer(r"python3\s+-c\s+" + DQ, text):
            i = m.end()
            while i < len(text):
                c = text[i]
                if c == "\\":
                    i += 2
                    continue
                if c == BT:
                    out.append((path, "ARM-A: backtick inside a double-quoted "
                                      "python3 -c body"))
                    break
                if c == DQ:
                    break
                i += 1
    if "D" in arms:
        # ARM D: an UNESCAPED $ that bash expands in the Python SOURCE.
        for m in re.finditer(r"python3\s+-c\s+" + DQ, text):
            body, _ = _dquote_body(text, m.end())
            base = text[:m.end()].count("\n")
            for dm in re.finditer(r"(?<!\\)\$([A-Za-z_][A-Za-z0-9_]*)", body):
                ln = base + body[:dm.start()].count("\n") + 1
                line = text.split("\n")[ln - 1].strip()
                if (_norm(path), line) in _SITE_ALLOW:
                    continue
                out.append((path, "ARM-D: unescaped $%s in a python3 -c body "
                                  "(line %d) -- pass it via sys.argv, or declare "
                                  "the site in _SITE_ALLOW" % (dm.group(1), ln)))
    if "B" in arms:
        # ARM B: a heredoc feeding python3 whose delimiter is UNQUOTED. The
        # delimiter must be a bare word, so a quoted one does not match by
        # construction — which is what separates the hazard from the safe form.
        for m in re.finditer(r"python3\b[^\n]*?<<-?\s*([A-Za-z_][A-Za-z0-9_]*)",
                             text):
            out.append((path, "ARM-B: unquoted heredoc (delimiter %s) feeds "
                              "python3" % m.group(1)))
    return out


def _is_generated_sidecar(name: str) -> bool:
    """The GENERATED sidecar class is NOT source (#17).

    An editing tool leaves a pre-image beside the file it touches, so a sidecar
    of a tool that was MID-EDIT carries the hazard the live file no longer has:
    while fixing #356, four sidecars of oc-harvest-dispatch held a backtick the
    lane had already removed, and the guard reddened on its own debris. The test
    is NARROW on purpose — suffix/infix only, never a bare "bak" substring — so
    a real source file named oc-bakery is still scanned.
    """
    return (name.endswith(".bak") or ".bak-" in name or ".pre-" in name)


def scan_tree(root, arms=("A", "B", "D")):
    files = []
    for dp, dn, fn in os.walk(str(root)):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
        files.extend(os.path.join(dp, f) for f in fn
                     if not _is_generated_sidecar(f))
    findings = []
    for f in sorted(files):
        try:
            text = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        findings.extend(scan_text(f, text, arms))
    return findings, len(files)


# =============================================================================
# fixture builders — hazard text assembled at RUNTIME, never in this source
# =============================================================================
def _c_body(body: str) -> str:
    return _C_OPEN + body + DQ


def _heredoc(delim: str, *, quoted: bool) -> str:
    d = (DQ + delim + DQ) if quoted else delim
    return "python3 - " + "<<" + d + "\nprint(1)\n" + delim + "\n"


def _write(p, text: str):
    p.write_text(text)
    return p


# =============================================================================
# ARM A / ARM B canaries and the SAFE control
# =============================================================================
@pytest.fixture
def hazard_file(tmp_path):
    """Both fences in one file, built by interpolation (see the module docstring)."""
    return _write(tmp_path / "hazard.sh",
                  _c_body("print(" + BT + "date" + BT + ")") + "\n"
                  + _heredoc("PYEOF", quoted=False))


@pytest.fixture
def safe_file(tmp_path):
    """The two SAFE forms: single-quoted -c, and a QUOTED heredoc delimiter."""
    return _write(tmp_path / "safe.sh",
                  "python3 -c 'print(1)'\n" + _heredoc("PYEOF", quoted=True))


def test_arm_a_sees_a_backtick_in_a_double_quoted_body(hazard_file):
    """§82 leg: ARM A must fire on the form the phantom command took."""
    msgs = [m for _, m in scan_text(hazard_file, hazard_file.read_text())]
    assert any("ARM-A" in m for m in msgs), (
        "ARM A cannot fire (canary unseen): %r" % msgs)


def test_arm_b_sees_an_unquoted_heredoc_feeding_python3(hazard_file):
    """§82 leg: ARM B must fire on the form that destroyed 1607 lines."""
    msgs = [m for _, m in scan_text(hazard_file, hazard_file.read_text())]
    assert any("ARM-B" in m for m in msgs), (
        "ARM B cannot fire (canary unseen): %r" % msgs)


def test_the_safe_fence_forms_stay_green(safe_file):
    """§82 leg (CONTROL): the guard must not fire on legitimate code.

    A rule that flagged every ``-c`` would be turned off within a week, which is
    why the safe half is asserted rather than assumed.
    """
    findings = scan_text(safe_file, safe_file.read_text())
    assert not findings, "the control fired on safe forms: %r" % findings


# =============================================================================
# the sidecar exclusion, and its NARROWNESS
# =============================================================================
def test_a_hazard_carrying_sidecar_is_not_a_site(tmp_path):
    """§82 leg (#17): the generated pre-image class is not source.

    The hazard is planted in sidecars ONLY (all three name forms) beside a CLEAN
    real file, so a guard that read a pre-image would fire here.
    """
    d = tmp_path / "sidecar"
    d.mkdir()
    hazard = _c_body("print(" + BT + "date" + BT + ")") + "\n"
    _write(d / "clean.sh", "python3 -c 'print(1)'\n")
    _write(d / "clean.sh.2026-10-05T120617.bak", hazard)
    _write(d / "clean.sh.bak-2026-10-05T120617", hazard)
    _write(d / "clean.sh.pre-2026-10-05T120617", hazard)
    findings, _ = scan_tree(d)
    assert not findings, "the pre-image class was scanned as source: %r" % findings


def test_the_sidecar_exclusion_is_narrow(tmp_path):
    """§82 leg (NEGATIVE CONTROL): a real file whose NAME merely contains "bak"
    is still source, and a hazard in it must still fire.

    Without this leg the exclusion could widen to a substring match and silently
    stop scanning real files.
    """
    d = tmp_path / "widen"
    d.mkdir()
    _write(d / "oc-bakery.sh", _c_body("print(" + BT + "date" + BT + ")") + "\n")
    findings, _ = scan_tree(d)
    assert any("ARM-A" in m for _, m in findings), (
        "widening control failed to fire: %r" % findings)


# =============================================================================
# ARM D — an unescaped $ in the -c body (#327)
# =============================================================================
def test_arm_d_sees_an_unescaped_dollar_in_a_c_body(tmp_path):
    """§82 leg (#327): bash would expand ``$NAME`` in the Python SOURCE."""
    f = _write(tmp_path / "dollar.sh",
               _c_body("\npath = " + DOL + "ROTATION_FILE\n") + "\n")
    msgs = [m for _, m in scan_text(f, f.read_text())]
    assert any("ARM-D" in m for m in msgs), (
        "ARM D cannot fire (canary unseen): %r" % msgs)


def test_a_regex_end_anchor_dollar_stays_green(tmp_path):
    """§82 leg (CONTROL): ``$`` before a non-name char is a regex anchor, inert.

    The pattern is ``(?<!\\\\)\\$([A-Za-z_][A-Za-z0-9_]*)``, so an end-anchor
    never matches it. This is what keeps the rule usable on real Python.
    """
    body = ("\nimport re\nprint(re.findall(r'[0-9]+" + DOL + "', s))\n")
    f = _write(tmp_path / "dollar-safe.sh", _c_body(body) + "\n")
    findings = scan_text(f, f.read_text())
    assert not findings, "the $ control fired on an inert anchor: %r" % findings


def test_the_dollar_allowlist_is_line_keyed_not_path_keyed(tmp_path):
    """§82 leg (CONTROL): the allowlist whitelists ONE reviewed line, not a file.

    The fixture sits at the ALLOWLISTED path (``tools/lib/oc_sqlite``) but
    carries a DIFFERENT interpolating line, so it must still fire.
    """
    d = tmp_path / "tools" / "lib"
    d.mkdir(parents=True)
    f = _write(d / "oc_sqlite",
               _c_body("\nfoo = " + DOL + "SOMETHING_ELSE\n") + "\n")
    findings, _ = scan_tree(tmp_path / "tools")
    assert any("ARM-D" in m for _, m in findings), (
        "the allowlist whitelisted a whole file: %r" % findings)


def test_the_allowlisted_line_itself_is_green():
    """The one surviving site must still be recognised, or the allowlist has
    silently become an unconditional exemption."""
    real = cf.TOOLS_DIR / "lib" / "oc_sqlite"
    if not real.is_file():
        pytest.skip("tools/lib/oc_sqlite is gone — the allowlist entry is stale")
    findings = scan_text(real, real.read_text())
    assert not findings, (
        "the allowlisted oc_sqlite line now reports %r — either the site moved "
        "or the allowlist key drifted from the file" % findings)


# =============================================================================
# the STATED blind spot — asserted, so nobody mistakes it for coverage
# =============================================================================
def test_command_substitution_in_a_double_quoted_body_is_a_known_gap(tmp_path):
    """``$(cmd)`` inside a double-quoted ``-c`` body is NOT detected.

    This is the guard's own documented blind spot: it cannot be told apart from
    a shell argument that follows the closing quote without a full parser. The
    leg asserts the GAP so that a future reader who widens the scanner sees this
    red and updates the docstring, rather than assuming the class was covered.
    """
    f = _write(tmp_path / "cmdsub.sh",
               _c_body("print(" + DOL + "(" + "date" + "))") + "\n")
    msgs = [m for _, m in scan_text(f, f.read_text())]
    assert not msgs, (
        "the $( ) blind spot CLOSED — good news, but update this module's "
        "docstring, which states the gap: %r" % msgs)


# =============================================================================
# every arm is load-bearing — a control that BLINDS the scanner must lose it
# =============================================================================
@pytest.mark.parametrize("arm,marker", [("A", "ARM-A"), ("B", "ARM-B"), ("D", "ARM-D")])
def test_each_arm_is_what_sees_its_canary(hazard_file, tmp_path, arm, marker):
    """NEGATIVE CONTROL: disable one arm and its canary must go UNSEEN.

    A canary leg can pass because the SCANNER is right or because the fixture
    would be caught by some other arm. This proves the arm under test is the
    one doing the work.
    """
    text = hazard_file.read_text()
    if arm == "D":
        f = _write(tmp_path / "dollar.sh",
                   _c_body("\npath = " + DOL + "ROTATION_FILE\n") + "\n")
        text = f.read_text()
    remaining = tuple(a for a in ("A", "B", "D") if a != arm)
    msgs = [m for _, m in scan_text("probe", text, arms=remaining)]
    assert not any(marker in m for m in msgs), (
        "with arm %s DISABLED the canary was still reported — the leg above is "
        "not measuring arm %s: %r" % (arm, arm, msgs))


# =============================================================================
# ARM C — the #323 symptom, seen by bash -n
# =============================================================================
def test_arm_c_sees_the_323_symptom(tmp_path, run_tool):
    """§82 leg: a stray interior ``"`` closes the body early, so bash -n fails.

    Built by interpolation: the "stray quote" is the hazard character.
    """
    broken = _write(tmp_path / "broken.sh",
                    "#!/usr/bin/env bash\n"
                    + _C_OPEN + "\nprint(1)  # a stray " + DQ + " here\nmore(\n"
                    + DQ + "\n")
    res = run_tool(["/bin/bash", "-n", str(broken)], timeout=60)
    assert res.rc != 0, (
        "ARM C control: bash -n PASSED a broken file — the detector is inert\n%s"
        % res.combined[-400:])


def _shell_tools():
    """The shell files ARM C scans: tracked, shebang-bash/sh, not tests/py/md."""
    res = subprocess.run(["git", "-C", str(cf.REPO_ROOT), "ls-files", "tools/*"],
                         capture_output=True, text=True)
    assert res.returncode == 0, "git ls-files failed: %s" % res.stderr[-400:]
    out = []
    for rel in res.stdout.splitlines():
        if not rel:
            continue
        if "/tests/" in rel or rel.endswith((".py", ".md", ".json", ".txt")):
            continue
        path = cf.REPO_ROOT / rel
        if not path.is_file():
            continue
        try:
            with open(path, "rb") as fh:
                first = fh.readline(200).decode("utf-8", "replace")
        except OSError:
            continue
        if not re.match(r"^#!.*(bash|/sh|sh\b)", first):
            continue
        out.append(path)
    return out


def test_arm_c_bash_syntax_is_clean_across_the_shell_tools(run_tool):
    """§82 legs: ``bash -n`` must pass on every shell tool, and must have
    scanned a non-zero population (a zero-scan would be an instrument failure,
    not a clean fleet).

    One batched ``bash -n`` loop rather than 56 subprocesses: the bound and the
    group kill still come from ``run_tool``, and a 56-way fork storm under load
    would cost more than it measures.
    """
    files = _shell_tools()
    assert len(files) >= SHELL_TOOL_FLOOR, (
        "ARM C enumerated only %d shell tool(s) (floor %d) — the instrument is "
        "broken, not the fleet" % (len(files), SHELL_TOOL_FLOOR))
    script = ('for f in "$@"; do /bin/bash -n "$f" 2>/dev/null || '
              'printf "BAD %s\\n" "$f"; done')
    res = run_tool(["/bin/bash", "-c", script, "_", *[str(f) for f in files]],
                   timeout=180)
    assert res.rc == 0, "the bash -n loop itself failed: %s" % res.combined[-400:]
    bad = [l.split(" ", 1)[1] for l in res.out.splitlines() if l.startswith("BAD ")]
    assert not bad, (
        "bash -n FAILS on %d/%d shell tool(s) (#327 ARM C): %s"
        % (len(bad), len(files), ", ".join(bad[:6])))


# =============================================================================
# the LIVE fleet
# =============================================================================
def test_no_hazard_site_in_the_fleet():
    """§82 leg: the fleet carries 0 sites today, and the first new one reds HERE.

    This is the CARRIER property: the section's value is not that it finds a
    site, it is that a site cannot land unnoticed.
    """
    findings, scanned = scan_tree(cf.TOOLS_DIR)
    assert scanned > SHELL_TOOL_FLOOR, (
        "the live scan walked only %d file(s) — the walker is broken" % scanned)
    assert not findings, (
        "%d hazard site(s):\n  %s" % (len(findings),
                                      "\n  ".join("%s: %s" % f for f in findings[:5])))


def test_this_module_is_itself_clean():
    """The canaries above are built by interpolation, so THIS file carries no
    literal hazard — otherwise the live scan would red on its own fixture.

    The shell makes the same move (``SQ_BT="$(printf '\\140')"``) and for the
    same reason; this leg is what stops a future edit from inlining one.
    """
    # Anchored on ``__file__``: the module is filed by SUBJECT now, so a
    # PYTEST_DIR / basename guess would miss and the guard below would
    # SILENTLY SKIP — a canary that skips is a canary that is not there.
    me = Path(__file__).resolve()
    if not me.is_file():
        pytest.skip("this module was renamed; update the leg")
    findings = scan_text(me, me.read_text())
    assert not findings, (
        "this module carries a LITERAL hazard, which the live scan would report "
        "as a real site: %r" % findings)
