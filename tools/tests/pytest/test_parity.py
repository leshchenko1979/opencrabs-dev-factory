"""COVERAGE PARITY between ``run.sh`` and the pytest suite — and old-vs-new equivalence.

Two questions, both answered with evidence rather than assertion:

1. **Coverage parity.** For every one of the 65 ``section "..."`` calls in
   ``tools/tests/run.sh``, does the pytest suite contain tests that assert
   something? A section with ZERO pytest assertions is the #120 defect wearing a
   new hat: ``chk()`` was called at ``run.sh:2105-2106`` and defined nowhere, so
   two legs asserted nothing while their section reported green. Counting that a
   test EXISTS is not enough; this module counts the ASSERTIONS.

2. **Old-vs-new equivalence.** For a representative sample, the same subject must
   reach the same verdict under both harnesses. Those legs are ``slow`` because
   they run ``run.sh --chunk N``; the census legs above them are parse-only and
   finish in milliseconds.

HOW THE TWO SIDES ARE COUNTED
-----------------------------
**Shell side** — one PASS-producing site per logical line, where a site is a
line mentioning ``ok``/``bad``/``chk``/``run_selftest``/``run_capture`` as a
word. Three details are load-bearing, and each was a bug in the first draft:

* ``ok "x" || bad "y"`` is **ONE** site, not two. Counting occurrences
  double-counted every ``ok || bad`` pair.
* A section's body runs from its ``section "..."`` call to the **next** call —
  not to the next ``# ---- `` header. The header-then-call convention means
  header-bounding truncates the body.
* **Heredoc bodies are masked.** ``run.sh`` feeds Python units and stub scripts
  through heredocs; their text is not shell assertions. Without masking, §13
  read 101 instead of 4 because its embedded Python unit was counted as shell.

**Pytest side** — an AST walk counting ``assert`` statements plus calls to
``pytest.fail``/``raises``/``warns``. That is a LOWER BOUND: it does not multiply
by ``parametrize`` cases, so a module with a 14-case table counts its single
``assert`` once. The real runtime assertion count is higher.

**The predicate above is the one this module uses, and it is reproducible.** An
earlier reconnaissance pass recorded a total of 503 with a slightly different
predicate that could not be reconstructed afterwards — a number nobody can
re-derive is a number nobody can trust, so the pinned baseline below is the
reproducible one and its totals are stated with it.

WHY THE REGISTER, NOT A BLANKET FAILURE
---------------------------------------
Seven sections currently assert FEWER things in pytest than in shell. That is a
real, honest finding — not a reason to weaken the check and not a reason to make
the suite red. So the deficits are a **pinned register** (``KNOWN_THIN``) and the
test asserts the live measurement equals it EXACTLY. The register is a ratchet:
a new deficit fails, and fixing one also fails until the register is updated. No
deficit can appear or vanish silently.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import conftest as cf

# The pytest ROOT, not this file's folder — the census reads modules filed in
# subfolders, and it stays correct if this module itself is ever refiled.
PYTEST_DIR = cf.PYTEST_DIR
RUN_SH = cf.REPO_ROOT / "tools" / "tests" / "run.sh"

# The suite is GROUPED BY SUBJECT — harness/, tools/, infra/, e2e/ — so a
# module's folder is a filing decision, not part of its identity. The census
# keys modules by BASENAME (the names below are unique; a duplicate would make
# this resolver ambiguous) and looks them up wherever they are filed.
MODULE_DIRS = ("", "harness", "tools", "infra", "e2e")

def module_path(name: str) -> Path:
    """The path of one test module, by basename, wherever it is filed."""
    for d in MODULE_DIRS:
        cand = (PYTEST_DIR / d / name) if d else (PYTEST_DIR / name)
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        "no module named %r under %s (looked in %r) — a rename that skipped this "
        "census would otherwise report zero assertion mass and pass"
        % (name, PYTEST_DIR, [d or "." for d in MODULE_DIRS]))

# =============================================================================
# the pinned census (reproducible — see the module docstring for the predicate)
# =============================================================================
# PASS-producing sites per ``section "..."`` call, in execution order. Section
# 18 is 0 because it is a header with no body (RETIRED); section 32's legs are
# all inside a heredoc-fed stub, so it contributes no shell ``ok``.
SHELL_SITES: dict[int, int] = {
    1: 24, 2: 6, 3: 4, 4: 4, 5: 3, 6: 8, 7: 8, 8: 1, 9: 2, 10: 15, 11: 4,
    12: 7, 13: 1, 14: 6, 15: 14, 16: 0, 17: 8, 18: 1, 19: 1, 20: 19, 21: 12,
    22: 3, 23: 2, 24: 3, 25: 1, 26: 1, 27: 1, 28: 6, 29: 1, 30: 0, 31: 11,
    32: 4, 33: 5, 34: 2, 35: 2, 36: 1, 37: 1, 38: 3, 39: 2, 40: 3, 41: 10,
    42: 8, 43: 8, 44: 5, 45: 9, 46: 2, 47: 2, 48: 2, 49: 5, 50: 5, 51: 7,
    52: 2, 53: 4, 54: 4, 55: 5, 56: 9, 57: 5, 58: 11, 59: 27, 60: 28, 61: 17,
    62: 65, 63: 26, 64: 16, 65: 3,
}

# §64 maps to TWO modules for a reason worth stating, because the number it
# produces is otherwise unexplainable. The census bounds a section's body by the
# NEXT ``section "..."`` CALL, and run.sh's oc-vendor-drift block (#700) opens on
# a bare ``# ---- 83.`` header with NO call of its own — so its nine ok/bad sites
# are charged to §64, the section that precedes them. They were never
# quoting-guard sites. Rather than re-bound every section (which would re-break
# §67 — see the docstring), the nine are paid back by ``test_vendor_drift.py``,
# which ports that block properly.
#
# Which pytest modules carry each section — read from each module's OWN docstring
# ("Ported: ... run.sh §N"), never from a second hand-written list. A module that
# renumbers without updating its docstring fails ``test_mapping_agrees_with_module_docstrings``.
SECTION_MODULES: dict[int, tuple[str, ...]] = {
    1: ("test_log_lib.py",),
    2: ("test_log_lib.py",),
    3: ("test_log_lib.py",),
    4: ("test_flood_guard.py",),
    5: ("test_flood_guard.py",),
    6: ("test_flood_guard.py",),
    7: ("test_wire.py",),
    8: ("test_verify_trio.py",),
    9: ("test_seal.py",),
    10: ("test_embed.py",),
    11: ("test_claims_predicate.py",),
    12: ("test_post_receipts.py",),
    13: ("test_usage_rc.py",),
    14: ("test_attrib.py",),
    15: ("test_attrib.py",),
    17: ("test_seal.py",),
    18: ("test_usage_rc.py",),
    19: ("test_usage_rc.py",),
    20: ("test_fanout.py",),
    21: ("test_deploy_stage.py", "test_e2e_deploy_stage.py"),
    22: ("test_ledger_edge.py",),
    23: ("test_review_persist.py",),
    24: ("test_gate.py",),
    25: ("test_post_receipts.py",),
    26: ("test_usage_rc.py",),
    27: ("test_usage_rc.py",),
    28: ("test_branch_sweep.py",),
    29: ("test_usage_rc.py",),
    30: ("test_ledger_edge.py",),
    31: ("test_ledger_lock_budget.py",),
    32: ("test_shadow_rotate.py",),
    33: ("test_smoke_evidence.py",),
    34: ("test_usage_rc.py",),
    35: ("test_usage_rc.py",),
    36: ("test_usage_rc.py",),
    37: ("test_usage_rc.py",),
    38: ("test_usage_rc.py",),
    39: ("test_usage_rc.py",),
    40: ("test_usage_rc.py",),
    41: ("test_rc_help.py",),
    42: ("test_rc_contract.py",),
    43: ("test_rc_contract.py",),
    44: ("test_notify_fanout.py",),
    45: ("test_health.py",),
    46: ("test_tool_contracts.py",),
    47: ("test_tool_contracts.py",),
    48: ("test_tool_contracts.py",),
    49: ("test_issue_dispatch.py",),
    50: ("test_tool_contracts.py",),
    51: ("test_fmt.py",),
    52: ("test_usage_rc.py",),
    53: ("test_notify_lib.py",),
    54: ("test_notify_lib.py",),
    55: ("test_snap.py",),
    56: ("test_snap.py",),
    57: ("test_harness_sigkill.py",),
    58: ("test_receipt_transcript.py",),
    59: ("test_oc_root_resolver.py",),
    60: ("test_quoting_guard.py", "test_vendor_drift.py"),
    61: ("test_entry_preamble.py", "test_harness_pool_mech.py"),
    62: ("test_cgroup.py", "test_harness_cgroup.py", "test_harness_pool.py", "test_harness_serialisation.py"),
    63: ("test_harness_lock.py",),
    64: ("test_harness_scratch.py",),
    65: ("test_harness_pytest_section.py",),
}

# Sections with NO pytest module, each with the reason it has none. A deferred
# section is NAMED, never silently absent — an omission a reader cannot see is
# indistinguishable from an oversight.
DEFERRED: dict[int, str] = {
    16: "RETIRED — the consent process was eliminated and the tool archived. "
        "The shell section is a header with no body: it asserts nothing, so a "
        "port would be an empty test inflating the pass count.",
}

# Sections whose pytest mass is currently BELOW their shell site count. Pinned,
# not ignored: the ratchet test below fails if this set changes in either
# direction, so a regression cannot hide and a fix cannot pass unnoticed.
KNOWN_THIN: dict[int, tuple[int, int]] = {
    10: (15, 4),
    20: (19, 18),
    41: (10, 5),
    51: (7, 5),
    64: (16, 14),
}

# =============================================================================
# live measurement
# =============================================================================
_CALL = re.compile(r'^section "(.*)"\s*$')
_SITE = re.compile(r"\b(ok|bad|chk|run_selftest|run_capture)\b")
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def _joined_lines() -> list[str]:
    """``run.sh`` with backslash continuations joined.

    A long ``ok "..." \\`` + continuation line is ONE logical line; counting the
    physical halves would double it.
    """
    out: list[str] = []
    buf = ""
    for line in RUN_SH.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.rstrip().endswith("\\"):
            buf += line.rstrip()[:-1] + " "
            continue
        out.append(buf + line)
        buf = ""
    if buf:
        out.append(buf)
    return out


def _mask_heredocs(lines: list[str]) -> list[str | None]:
    """``None`` for every line INSIDE a heredoc body, and for its fences.

    A heredoc must have a real closing delimiter; without that check a stray
    ``<<`` in a comment opens a body that never closes and swallows the rest of
    the file, taking the whole census to zero.
    """
    out: list[str | None] = list(lines)
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("#"):
            i += 1
            continue
        m = _HEREDOC.search(lines[i])
        if not m:
            i += 1
            continue
        delim = m.group(2)
        close = next((j for j in range(i + 1, len(lines)) if lines[j].strip() == delim), None)
        if close is None:                       # not a real heredoc — a stray <<
            i += 1
            continue
        for j in range(i, close + 1):
            out[j] = None
        i = close + 1
    return out


def shell_census() -> tuple[list[str], dict[int, int]]:
    """``(section_titles, {ordinal: pass_site_count})`` measured from run.sh now."""
    lines = _joined_lines()
    masked = _mask_heredocs(lines)
    calls = [(i, _CALL.match(l).group(1)) for i, l in enumerate(lines) if _CALL.match(l)]
    titles = [t for _i, t in calls]
    counts: dict[int, int] = {}
    for idx, (ln, _title) in enumerate(calls, start=1):
        end = calls[idx][0] if idx < len(calls) else len(lines)
        n = 0
        for body_line in masked[ln + 1:end]:
            if body_line is None:
                continue
            s = body_line.strip()
            if not s or s.startswith("#"):
                continue
            if _SITE.search(s):
                n += 1
        counts[idx] = n
    return titles, counts


def module_mass(name: str) -> int:
    """Assertion sites in one module — a LOWER BOUND (parametrize not multiplied)."""
    tree = ast.parse(module_path(name).read_text(encoding="utf-8", errors="replace"))
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            n += 1
        elif isinstance(node, ast.Call):
            f = node.func
            fn = (f.attr if isinstance(f, ast.Attribute)
                  else f.id if isinstance(f, ast.Name) else "")
            if fn in ("fail", "raises", "warns"):
                n += 1
    return n


def section_mass(sec: int) -> int:
    return sum(module_mass(m) for m in SECTION_MODULES.get(sec, ()))

# =============================================================================
# 1. COVERAGE PARITY — the census
# =============================================================================
def test_run_sh_still_has_sixty_eight_sections():
    """The census is keyed by ordinal, so a renumber invalidates every row."""
    titles, counts = shell_census()
    assert len(titles) == 65, (
        "run.sh has %d ``section`` calls, the census pins 65 — a section was "
        "added or removed; re-derive SHELL_SITES rather than widening this bound"
        % len(titles))

def test_pinned_census_still_matches_run_sh():
    """The pinned baseline must still describe the file on disk.

    A drift here means run.sh changed under the census. Re-derive, do not guess.
    """
    _titles, counts = shell_census()
    drift = {s: (SHELL_SITES.get(s), counts.get(s))
             for s in set(SHELL_SITES) | set(counts)
             if SHELL_SITES.get(s) != counts.get(s)}
    assert not drift, (
        "the shell census drifted from the pinned baseline (ordinal: pinned, live): %r — "
        "re-measure SHELL_SITES, and check whether the change is a lost assertion "
        "before you update it" % (drift,))

def test_every_section_is_accounted_for():
    """No section may be silently absent: each is mapped, deferred, or retired."""
    titles, counts = shell_census()
    unaccounted = [s for s in counts if s not in SECTION_MODULES and s not in DEFERRED]
    assert not unaccounted, (
        "sections %r have neither a pytest module nor a DEFERRED reason — a port "
        "that quietly dropped them is the defect this whole module exists to catch"
        % (unaccounted,))
    stale = [s for s in list(SECTION_MODULES) + list(DEFERRED) if s not in counts]
    assert not stale, (
        "the mapping names sections %r that no longer exist in run.sh" % (stale,))

def test_deferred_sections_are_named_with_a_reason():
    """A deferred section carries prose, not a shrug — and never a silent skip."""
    for sec, reason in DEFERRED.items():
        assert reason and len(reason) > 40, (
            "§%d is deferred with %r — every deferral needs the reason a reader "
            "would otherwise have to guess" % (sec, reason))
    # §16 asserts nothing at all (a retired header with no body). §62 was the
    # last other entry: its deferral claimed run.sh's own bad() accumulator had no
    # pytest-side equivalent, but that was a claim about WHERE THE FUNCTIONS LIVE.
    # They are text in run.sh, so lib/harness extracts them verbatim and
    # test_receipt_transcript.py drives the real ones (§33's deferral was
    # withdrawn for the same reason).
    assert set(DEFERRED) == {16}, (
        "the deferred set changed to %r — update the README's 'Not ported' table "
        "in the same commit" % (sorted(DEFERRED),))

def test_no_deferred_section_has_a_pytest_module_that_ports_it():
    """THE STALENESS GUARD: a ported section may not stay in ``DEFERRED``.

    This is the failure mode that made this census lie. §33, §63 and §64 each
    landed as a real module on their own branch while this register still said
    "no pytest module, here is why" — so the census reported ZERO coverage for
    three sections that were fully covered, and every test above stayed GREEN
    because a deferred section is never asked for its mass. A register that is
    only checked for internal consistency cannot notice the world moving.

    The check is deliberately mechanical: take the section's title from run.sh,
    strip the parenthesised issue refs and glosses, and ask whether any mapped
    module's own docstring already carries those words. A module whose docstring
    names the subject is a module that ports it. Requiring the FULL token set
    keeps this off accidental neighbours: a true match scores 1.0 while the
    best false candidate scores 0.5.

    What this cannot see is a section ported under a title that shares no words
    with run.sh's — no mechanical check can, and inventing a fuzzy threshold to
    cover it would red on legitimate near-misses instead.
    """
    titles, _counts = shell_census()
    stop = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "with",
            "not", "is", "are", "it", "no", "every", "all", "one", "per", "by",
            "from", "as", "at", "that", "this", "its"}

    def tokens(text: str) -> set[str]:
        text = re.sub(r"\(#[^)]*\)", "", text)          # (issues)
        text = re.sub(r"\([^)]*\)", "", text)           # (glosses)
        return {w for w in re.findall(r"[a-z0-9][a-z0-9_.-]*", text.lower())
                if w not in stop and len(w) > 2}

    docs = {}
    for mod in {m for mods in SECTION_MODULES.values() for m in mods}:
        doc = ast.get_docstring(ast.parse(
            module_path(mod).read_text(encoding="utf-8", errors="replace"))) or ""
        docs[mod] = tokens(doc)

    ported = []
    for sec in sorted(DEFERRED):
        want = tokens(titles[sec - 1])
        if not want:
            continue
        for mod, have in docs.items():
            if want <= have:
                ported.append("§%d (%r) is DEFERRED but %s already ports it"
                              % (sec, titles[sec - 1], mod))
    assert not ported, (
        "the deferred register is STALE — these sections now have a module of "
        "their own, so the census is reporting zero coverage that exists:\n  %s\n"
        "Move each to SECTION_MODULES, drop its DEFERRED entry, and re-derive "
        "KNOWN_THIN in the same commit." % "\n  ".join(ported))

def test_zero_assertion_sections_are_the_declared_ones():
    """Exactly §16 and §30 assert nothing in shell — and both are deliberate.

    §16 is a retired header with no body. §30's legs live inside a heredoc-fed
    stub, so they carry no shell ``ok``. Any OTHER zero is a section that
    reported green while asserting nothing — the #120 shape.
    """
    _titles, counts = shell_census()
    zero = sorted(s for s, n in counts.items() if n == 0)
    assert zero == [16, 30], (
        "sections %r assert nothing in shell; only [16, 30] are declared — a new "
        "one is a section whose green verdict rests on no assertion at all" % (zero,))

@pytest.mark.parametrize("sec", sorted(SECTION_MODULES))
def test_mapped_section_has_pytest_assertions(sec):
    """THE #120 GUARD: a mapped section must assert something in pytest too.

    A section whose pytest mass is zero is the ``chk()`` defect one layer up —
    tests that exist, run, and prove nothing.
    """
    mass = section_mass(sec)
    assert mass > 0, (
        "run.sh §%d (%r) is mapped to %r but those modules carry ZERO assertion "
        "sites — the section's coverage exists on paper only (#120)"
        % (sec, shell_census()[0][sec - 1], SECTION_MODULES[sec]))

def test_every_mapped_module_exists_and_declares_its_scope():
    """A mapped module must exist, carry assertions, and say what it ports.

    NOTE the numbering trap this test is deliberately written around. Three
    schemes coexist in this repo and they do NOT agree:

    * this census keys sections by the **positional ordinal** of the ``section``
      call (1..65), because that is what ``--chunk N`` selects;
    * ``run.sh``'s own ``# ---- `` headers carry **labels** (``00b``, ``00b2``,
      ``00d``, ``66b``) which are not a 1..N sequence;
    * ported module docstrings cite the explorer report's numbers (``§01/§02/§03``
      for the verify trio, which is ordinal 8/9/10).

    So a numeric comparison between the docstring and this mapping tests the
    FORMATTING, not the coverage — it fails on the verify trio for a reason that
    is not a defect. What is checkable is that each mapped module exists, asserts
    something, and declares a port scope of its own rather than being an
    accidental catch-all.
    """
    for sec, mods in SECTION_MODULES.items():
        assert mods, "§%d has an empty module tuple — map it or defer it" % sec
        for mod in mods:
            path = module_path(mod)
            assert path.exists(), (
                "§%d is mapped to %s, which does not exist — the mapping points at "
                "a module that was renamed or removed" % (sec, mod))
            doc = ast.get_docstring(ast.parse(
                path.read_text(encoding="utf-8", errors="replace"))) or ""
            assert re.search(r"§\d+|Section \d+|run\.sh", doc), (
                "%s is mapped to §%d but its docstring does not name a run.sh "
                "section at all — a reader cannot tell what it ports" % (mod, sec))

def test_coverage_register_is_current():
    """The thin-coverage register is a RATCHET: it must equal the live deficit.

    A new deficit fails (a port lost coverage). A fixed one fails too (the
    register is stale, and leaving it stale is how the next real regression hides
    behind a row nobody re-reads).
    """
    live = {sec: (SHELL_SITES[sec], section_mass(sec))
            for sec in SECTION_MODULES
            if section_mass(sec) < SHELL_SITES[sec]}
    assert live == KNOWN_THIN, (
        "thin-coverage register is stale.\n  newly thin: %r\n  now covered: %r\n"
        "  live: %r\n  pinned: %r"
        % (sorted(set(live) - set(KNOWN_THIN)),
           sorted(set(KNOWN_THIN) - set(live)),
           live, KNOWN_THIN))

def test_pytest_total_does_not_regress():
    """The suite's total assertion mass is a floor, not a target.

    Individual sections can be thin; the whole must not shrink. This is the
    coarse guard behind the per-section one — it catches mass deleted from a
    module nobody thought to re-map.
    """
    total = sum(module_mass(m) for m in {m for mods in SECTION_MODULES.values() for m in mods})
    assert total >= 560, (
        "the mapped modules now carry %d assertion sites, down from the 560 "
        "floor — assertions were deleted somewhere" % total)

# =============================================================================
# 2. OLD-VS-NEW EQUIVALENCE (slow — runs the real shell chunks)
# =============================================================================
# A representative sample, one per failure class rather than one per section:
#   §4/§5/§6  a guard with a FALSE-POSITIVE direction (3 rows must not trip it)
#   §12       a table-driven decoder (many legs, one loop)
#   §40       rc-table integrity (shell quoting of unescaped pipes)
#   §53       repo/installed identity (two arms, one verdict)
#   §62       a fail-path transcript (the RED direction, not just green)
#
# These run ``run.sh --chunk N``, so they are minutes, not milliseconds, and they
# are marked ``slow``. The env below is REQUIRED: without it the chunk inherits
# the live battery's lock and TMPDIR and two concurrent runs corrupt each other.
EQUIVALENCE_SAMPLE = [
    (4, "test_flood_guard.py", "flood guard reads both timestamp forms"),
    (12, "test_embed.py", "lib/oc-embed.sh (job-name embed decoder)"),
    (40, "test_usage_rc.py", "oc-rebase-safety"),
    (53, "test_fmt.py", "oc-fmt repo/installed identity"),
]


def _chunk_env(tmp: Path) -> dict[str, str]:
    import os
    env = dict(os.environ)
    env.pop("BATTERY_IN_CHUNK", None)          # a chunk must not think it is nested
    # env_guard redirects these two into pytest's scratch, and run.sh's tools
    # isolate themselves with a fake HOME instead. Letting the redirect through
    # defeats that isolation: a tool whose selftest seeds its own ledger then
    # reads pytest's instead and reports a failure unrelated to the code.
    env.pop("OC_DEV_STATE", None)
    env.pop("OC_FANOUT_LEDGER", None)
    env["OC_BATTERY_NO_CGROUP"] = "1"          # no re-exec mid-test
    env["OC_BATTERY_NO_PRIORITY"] = "1"        # no nice/ionice games
    env["OC_BATTERY_LOCK"] = str(tmp / "lk")   # our own lock, not the live one
    env["OC_BATTERY_TEST_TMPDIR"] = str(tmp / "root")
    return env


@pytest.mark.slow
@pytest.mark.parametrize("sec,module,title", EQUIVALENCE_SAMPLE,
                         ids=[t for _s, _m, t in EQUIVALENCE_SAMPLE])
def test_chunk_and_module_agree(sec, module, title, tmp_path):
    """The same subject reaches the same verdict under both harnesses.

    The assertion is on the VERDICT (rc == 0), never on the ok-count: the two
    harnesses group assertions differently by design — six shell selftest legs
    become one parametrized pytest leg — so an ok-count equality would be a test
    of the translation's style, not of its correctness.
    """
    import subprocess

    env = _chunk_env(tmp_path)
    shell = subprocess.run(["bash", str(RUN_SH), "--chunk", str(sec)],
                           capture_output=True, text=True, env=env, timeout=1800)
    assert shell.returncode == 0, (
        "run.sh --chunk %d (§%s) failed rc=%d\n--- tail ---\n%s"
        % (sec, title, shell.returncode, shell.stdout[-3000:]))

    new = subprocess.run(["python3", "-m", "pytest", str(module_path(module)),
                          "-q", "-n", "0", "-p", "no:cacheprovider"],
                         capture_output=True, text=True, cwd=str(cf.REPO_ROOT),
                         env=env, timeout=1800)
    assert new.returncode == 0, (
        "%s failed while run.sh --chunk %d (§%s) passed — the port and the shell "
        "DISAGREE about the same subject\n--- tail ---\n%s"
        % (module, sec, title, new.stdout[-3000:]))
