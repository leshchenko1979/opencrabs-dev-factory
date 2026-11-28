"""The WRITE verbs, differential against the bash tool (factory #204, phase 3).

``test_ledger_core.py`` proves the STORE layer and diffs the READ verbs. It has
no write-verb coverage at all — 886 lines of write path that had never been run
side by side with the tool it is replacing. This file is that gap.

The contract is the same one the read-verb leg states: **byte identity is the
gate, not a nicety.** For each verb the SAME fixture is built twice, once per
binary, and compared on four surfaces:

* ``rc``
* ``stdout``
* ``stderr``
* **the ledger afterwards** — ``events.jsonl`` AND ``workers.json`` bytes,
  plus every other file the verb wrote in the state dir. Comparing stdout alone
  passes a port that appends the right line to the wrong store, or that rewrites
  the roster when only an event changed (spec trap 3).

Two surfaces are inherently clock- or commit-dependent and are normalised, not
ignored: ``now_iso()`` stamps and the short sha the git tail echoes. Everything
else must match exactly, so a real divergence cannot hide behind a scrubber —
``_norm`` touches only an ISO-8601 stamp, a ``YYYYMMDDTHHMMSSZ`` freeze stamp,
and a ``sha=<hex>`` echo.

WHY THE FIXTURE LOOKS LIKE THIS (the recipe is load-bearing, not decorative)
---------------------------------------------------------------------------
* ``events.jsonl`` is seeded with ONE bootstrap row. A bare/empty record is
  REFUSED by BOTH binaries ("ledger missing or unparseable"), so a zero-row
  fixture exercises the refusal path and nothing else.
* ``OC_DEV_STATE`` is never set to the empty string. Set-but-empty and unset
  take different branches in the bash, so a test that pins it to "" would be
  comparing two tools on a shape the fleet never produces.
* Both binaries run against the SAME absolute path, rebuilt between runs. A
  tmpdir-per-run fixture puts two different paths into the output and turns
  every path mention into a false divergence — which is exactly how the first
  three attempts at this harness were wasted.
* ``workers-ledger.json`` is REMAPPED by both binaries to a sibling
  ``events.jsonl``; the migrate cases rely on the opposite (no sibling, so the
  legacy file stays the source), which is why they build a legacy fixture.

KNOWN DIVERGENCES
-----------------
Two, both in ``sweep-closed-claims``, both recorded by their own test below
rather than smoothed over. See the module-level ``KNOWN_DIVERGENCES`` table.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

import pytest

import conftest as cf

PY_TOOL = cf.TOOLS_DIR / "state" / "oc-ledger.py"
BASH_TOOL = cf.LEDGER_BASH   # pre-flip bash; the live path is the shim

ACTOR = cf.LEDGER_ACTOR
EDITOR = "11111111-1111-1111-1111-111111111111"
NEWBIE = "22222222-2222-2222-2222-222222222222"

# The write verbs the tool implements. ``selftest`` is deliberately absent: the
# pytest oracle IS the selftest, so porting it would be porting the thing under
# test. Every name here must appear in at least one parity case (asserted by
# test_every_write_verb_has_a_parity_case), so a new verb cannot land untested.
WRITE_VERBS = (
    "stamp", "fixture", "sync", "ack", "enroll", "promote", "retire",
    "commit-pending", "confirm", "migrate", "claim", "claim-ref",
    "sweep-closed-claims",
)

# ---------------------------------------------------------------------------
# normalisation — ONLY clock reads and commit shas
# ---------------------------------------------------------------------------
_ISO = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
_FREEZE = re.compile(r"\d{8}T\d{6}Z")
_SHA = re.compile(r"sha=[0-9a-f]{7,40}")
_SHA40 = re.compile(r"\b[0-9a-f]{40}\b")


def _norm(text):
    """Scrub the three values a run cannot reproduce, and nothing else."""
    text = _SHA40.sub("<SHA40>", text)
    text = _SHA.sub("sha=<SHA>", text)
    text = _FREEZE.sub("<FREEZE>", text)
    text = _ISO.sub("<TS>", text)
    return text


# ---------------------------------------------------------------------------
# the fixture
# ---------------------------------------------------------------------------
BASE_ROWS = [{"n": 1, "kind": "bootstrap", "ts": "2026-01-01T00:00:00Z"}]
BASE_WORKERS = [{"uuid": EDITOR, "role": "editor", "topic_id": 3,
                 "state": "ACTIVE"}]
# One OPEN claim on #7, so sweep-closed-claims has a population to judge.
CLAIM_ROWS = BASE_ROWS + [
    {"n": 2, "t": "2026-01-01T00:00:01Z", "by": EDITOR, "kind": "claim",
     "what": "CLAIM #7 taking it", "issues": [7]},
]


def _git(path, *args):
    """git with identity pinned via -c (never the container's global config)."""
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t",
         "-c", "commit.gpgsign=false", "-C", str(path), *args],
        capture_output=True, text=True)


def _gh_stub(root, mode):
    """A ``gh`` on PATH: ``empty`` answers ``[]``; ``fail`` exits 1.

    ``sweep-closed-claims`` shells out to ``gh`` for both issue states. A stub
    keeps the verb offline and, more importantly, DETERMINISTIC — the real
    probe's answer depends on GitHub, which would make the leg flaky rather
    than differential.
    """
    bindir = os.path.join(root, "bin")
    os.makedirs(bindir, exist_ok=True)
    stub = os.path.join(bindir, "gh")
    with open(stub, "w", encoding="utf-8") as fh:
        if mode == "fail":
            fh.write("#!/bin/sh\necho 'gh: not authenticated' >&2\nexit 1\n")
        else:
            fh.write("#!/bin/sh\necho '[]'\nexit 0\n")
    os.chmod(stub, 0o755)
    return bindir


def build_fixture(root, *, rows=None, workers=None, legacy=False,
                  skill_version="0.4.2", receipt=True,
                  changelog="## v0.4.2\nentry\n", gh="empty",
                  src_text=None, dirty_events=False):
    """(state, skill, env) — the whole sandbox, byte-identical every call."""
    shutil.rmtree(root, ignore_errors=True)
    # A BARE/EMPTY events.jsonl is REFUSED by BOTH binaries ("ledger missing or
    # unparseable"), so the default base is ONE bootstrap row, never zero rows.
    # An explicit ``rows=[]`` still means a deliberately-empty record (the
    # migrate cases need one), which is why the default is applied on ``is
    # None`` and NOT with ``rows or ...``.
    if rows is None:
        rows = BASE_ROWS
    state = os.path.join(root, "state")
    skill = os.path.join(root, "skill")
    os.makedirs(os.path.join(skill, "tools", "tests"))
    os.makedirs(state)

    if legacy:
        # migrate's SOURCE: a single-file record with no events.jsonl sibling,
        # so neither binary remaps the path away from it.
        body = src_text if src_text is not None else json.dumps(
            {"workers": workers or [], "events": rows})
        with open(os.path.join(state, "workers-ledger.json"), "w",
                  encoding="utf-8") as fh:
            fh.write(body)
    else:
        with open(os.path.join(state, "events.jsonl"), "w",
                  encoding="utf-8") as fh:
            fh.write("".join(json.dumps(r) + "\n"
                             for r in (BASE_ROWS if rows is None else rows)))
        with open(os.path.join(state, "workers.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"workers": (BASE_WORKERS if workers is None
                                   else workers)}, fh)

    with open(os.path.join(skill, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("name: fixture\nversion: %s\n---\n# fixture\n" % skill_version)
    with open(os.path.join(skill, "CHANGELOG.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# fixture changelog\n" + changelog)
    # v0.4.157: keep tools/ TRACKED. An entirely-untracked directory collapses
    # to `?? tools/` in porcelain, which the stray-guard reads as another lane's
    # dirty work.
    open(os.path.join(skill, "tools", "tests", ".keep"), "w").close()
    if receipt:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(os.path.join(skill, "tools", "tests", "battery-last.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"verdict": "PASS", "fail": 0, "ts": ts}, fh)

    for repo in (state, skill):
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "t@t")
        _git(repo, "config", "user.name", "t")
        _git(repo, "config", "commit.gpgsign", "false")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")

    if dirty_events:
        # A committed base, then one uncommitted row: the commit-pending window
        # (HEAD n vs disk n) is only non-zero in this shape.
        with open(os.path.join(state, "events.jsonl"), "a",
                  encoding="utf-8") as fh:
            fh.write(json.dumps({"n": 2, "kind": "note", "what": "unpushed"})
                     + "\n")

    bindir = _gh_stub(root, gh)
    # In LEGACY mode the record IS workers-ledger.json: pointing OC_LEDGER at
    # events.jsonl (which does not exist yet) makes `migrate` die rc 2 "source
    # ledger not found" — measured. The bash's parse_global only remaps
    # workers-ledger.json -> events.jsonl when the legacy file is GONE, so
    # naming the legacy file here keeps it the source, which is exactly the
    # state migrate is meant to convert.
    record = (os.path.join(state, "workers-ledger.json") if legacy
              else os.path.join(state, "events.jsonl"))
    env = {
        "OC_LEDGER": record,
        "OC_SKILL_DIR": skill,
        "OC_DEPLOY_STATE_DIR": state,
        "HOME": root,
        "OC_ACTOR": ACTOR,
        "OC_TOOLS_NOLOG": "1",
        "OC_SHIP_AUDIT_CHAIN": "0",
        "OC_LEDGER_LOCK_WAIT": "3",
        "OC_LEDGER_PUSH_TIMEOUT": "1",
        "OC_LEDGER_PUSH_MIN": "99",       # never trigger a network push
        "OC_LEDGER_GIT_TAIL_WAIT": "20",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "PATH": bindir + os.pathsep + os.environ.get("PATH", ""),
    }
    return state, skill, env


def snapshot(root):
    """Every file the verb could have written, normalised. ``.git`` excluded.

    The git object store is excluded because a commit's identity depends on the
    clock; the LEDGER and the roster are not, because those are the bytes the
    verb is answerable for.
    """
    out = {}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        if os.path.basename(dirpath) == "bin":
            continue
        for name in files:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if rel.endswith(".lock"):
                continue
            try:
                with open(path, "rb") as fh:
                    body = fh.read()
            except OSError:
                continue
            out[_norm(rel)] = _norm(body.decode("utf-8", "surrogateescape"))
    return out


def run_pair(root, argv, run_tool, **build_kw):
    """(bash, py) as ``(rc, out, err, files)`` — same path, rebuilt per run."""
    results = {}
    for label, cmd in (("bash", [str(BASH_TOOL), *argv]),
                       ("py", [sys.executable, str(PY_TOOL), *argv])):
        _state, _skill, env = build_fixture(root, **build_kw)
        res = run_tool(cmd, timeout=90, env=env)
        results[label] = (res.rc, _norm(res.out), _norm(res.err),
                          snapshot(root))
    return results["bash"], results["py"]


def _explain(name, bash, py):
    """A failure message that names the surface that diverged, not just 'differ'."""
    parts = ["verb %r diverges from the bash port" % (name,)]
    if bash[0] != py[0]:
        parts.append("  rc      bash=%r py=%r" % (bash[0], py[0]))
    if bash[1] != py[1]:
        parts.append("  stdout  bash=%r\n          py  =%r"
                     % (bash[1][-600:], py[1][-600:]))
    if bash[2] != py[2]:
        parts.append("  stderr  bash=%r\n          py  =%r"
                     % (bash[2][-600:], py[2][-600:]))
    if bash[3] != py[3]:
        for key in sorted(set(bash[3]) | set(py[3])):
            if bash[3].get(key) != py[3].get(key):
                parts.append("  FILE %s\n    bash=%r\n    py  =%r"
                             % (key, bash[3].get(key), py[3].get(key)))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# the cases — one row per shape worth diffing
# ---------------------------------------------------------------------------
CASES = [
    # --- stamp: the append path, the issue tokenizer, the kind gate ---------
    ("stamp-note", ["stamp", "note", "hello world"], {}),
    ("stamp-claim", ["stamp", "claim", "CLAIM #42 doing it"], {}),
    ("stamp-unclaim", ["stamp", "unclaim", "#5 — stale"], {}),
    ("stamp-done", ["stamp", "done", "#9 shipped"], {}),
    ("stamp-unicode", ["stamp", "note", "a — b · c"], {}),
    ("stamp-unknown-kind", ["stamp", "frobnicate", "x"], {}),
    ("stamp-no-args", ["stamp"], {}),
    ("stamp-help", ["stamp", "--help"], {}),
    # --- ack: roster gate, idempotent re-ack -------------------------------
    ("ack", ["ack", EDITOR, "0.4.2"], {}),
    ("ack-unknown-uuid", ["ack", NEWBIE, "0.4.2"], {}),
    # --- roster lifecycle ---------------------------------------------------
    ("enroll", ["enroll", NEWBIE, "editor", "--topic", "5"], {}),
    ("enroll-no-topic", ["enroll", NEWBIE, "editor"], {}),
    ("promote", ["promote", EDITOR, "hq"], {}),
    ("retire", ["retire", EDITOR], {}),
    # --- confirm / claim ----------------------------------------------------
    ("confirm", ["confirm", EDITOR], {}),
    ("claim", ["claim", EDITOR, "#7", "taking it"], {}),
    ("claim-ref", ["claim-ref", EDITOR], {"rows": CLAIM_ROWS}),
    # --- sweep-closed-claims: dry-run only (the live arm writes rows) ------
    ("sweep-no-claims-dry-run", ["sweep-closed-claims", "--dry-run"], {}),
    ("sweep-unresolved-dry-run", ["sweep-closed-claims", "--dry-run"],
     {"rows": CLAIM_ROWS}),
    # --- fixture: the bulk seeder ------------------------------------------
    ("fixture", ["fixture", "--n", "5", "--t", "2026-01-02T00:00:00Z",
                 "--kind", "note", "--by", "tester", "--what", "seeded"], {}),
    # --- sync: version gate + CHANGELOG gate + the bump event --------------
    ("sync-happy", ["sync", "--version", "0.4.2", "--why", "parity"], {}),
    ("sync-no-why", ["sync", "--version", "0.4.2"], {}),
    ("sync-bad-shape", ["sync", "--version", "1.2", "--why", "x"], {}),
    ("sync-version-step", ["sync", "--version", "0.4.7", "--why", "x"], {}),
    ("sync-missing-changelog", ["sync", "--version", "0.4.2", "--why", "x"],
     {"changelog": "# no entry here\n"}),
    # --- commit-pending: the three-way verdict -----------------------------
    ("commit-pending-clean", ["commit-pending"], {}),
    ("commit-pending-window", ["commit-pending"], {"dirty_events": True}),
    ("commit-pending-bundle", ["commit-pending", "--bundle"], {}),
    ("commit-pending-help", ["commit-pending", "--help"], {}),
    # --- migrate: the riskiest verb, rewrites in place ---------------------
    ("migrate-ok", ["migrate", "--to", "jsonl"],
     {"legacy": True,
      "rows": [{"n": 1, "kind": "note", "what": "legacy row"}]}),
    ("migrate-help", ["migrate", "--help"], {"legacy": True, "rows": []}),
    ("migrate-no-target", ["migrate"], {"legacy": True, "rows": []}),
    ("migrate-bad-target", ["migrate", "--to", "yaml"],
     {"legacy": True, "rows": []}),
    ("migrate-missing-source", ["migrate", "--to", "jsonl"],
     {"legacy": True, "rows": [], "src_text": "{not json"}),
    ("migrate-empty-events", ["migrate", "--to", "jsonl"],
     {"legacy": True, "rows": []}),
    ("migrate-scalar-source", ["migrate", "--to", "jsonl"],
     {"legacy": True, "src_text": "5"}),
    ("migrate-object-events", ["migrate", "--to", "jsonl"],
     {"legacy": True, "src_text": '{"events":{"a":1,"b":2}}'}),
]

CASE_IDS = [case[0] for case in CASES]


@pytest.mark.parametrize("name,argv,build_kw", CASES, ids=CASE_IDS)
def test_write_verb_is_byte_identical(name, argv, build_kw, scratch, run_tool):
    """rc, stdout, stderr AND the resulting ledger bytes must all match.

    The ledger snapshot is the half the read-verb differential never had: a
    writer can print the right line and still persist the wrong store, or
    rewrite ``workers.json`` when only an event changed.
    """
    root = str(scratch.path / "parity" / name)
    bash, py = run_pair(root, argv, run_tool, **build_kw)
    assert (py[0], py[1], py[2], py[3]) == (bash[0], bash[1], bash[2], bash[3]), \
        _explain(name, bash, py)


# ---------------------------------------------------------------------------
# coverage guard — a new verb cannot land without a parity case
# ---------------------------------------------------------------------------
def test_every_write_verb_has_a_parity_case(scratch, run_tool):
    """The tool's own ``--verbs`` is the authority on what it implements.

    A hand-kept list in the test would drift from the tool the moment a verb is
    added, and the drift reads as full coverage. So the list is READ FROM THE
    BINARY and compared against the cases above: an unported or untested verb
    reds this leg by name.
    """
    env = {"OC_TOOLS_NOLOG": "1"}
    res = run_tool([sys.executable, str(PY_TOOL), "--verbs"], timeout=30,
                   env=env)
    assert res.rc == 0, "--verbs failed: %r" % (res.err,)
    declared = set(res.out.split())
    exercised = {case[1][0] for case in CASES}

    missing = sorted(set(WRITE_VERBS) - exercised)
    assert not missing, (
        "write verbs in WRITE_VERBS with NO parity case — they would ship "
        "unverified: %s" % missing)

    # The READ verbs are diffed by test_ledger_core.py, not here. But every
    # write verb this file claims MUST exist in the binary's --verbs, or the
    # case is testing a name the tool dropped.
    declared = set(res.out.split())
    bogus = sorted(exercised - declared)
    assert not bogus, "parity cases name verbs the tool does not declare: %s" % bogus


def test_write_verb_list_matches_the_bash(scratch, run_tool):
    """``--verbs`` is byte-identical, so the two tools advertise one surface."""
    env = {"OC_TOOLS_NOLOG": "1"}
    bash = run_tool([str(BASH_TOOL), "--verbs"], timeout=30, env=env)
    py = run_tool([sys.executable, str(PY_TOOL), "--verbs"], timeout=30,
                  env=env)
    assert (py.rc, py.out, py.err) == (bash.rc, bash.out, bash.err)


# ---------------------------------------------------------------------------
# KNOWN DIVERGENCES — recorded, never smoothed over
# ---------------------------------------------------------------------------
KNOWN_DIVERGENCES = {
    "sweep-probe-failure-stderr": (
        "sweep-closed-claims, gh probe FAILS. rc is identical (3) and the "
        "final 'scan failed (rc 4)' line is identical. The bash captures the "
        "probe's stderr into $TMPDIR/oc-sweep-closed-claims.$$.err and then "
        "`rm -f`s it WITHOUT READING, so the operator never learns WHY the "
        "scan failed. The Python additionally prints the gh diagnostic. This "
        "is documented in _probe_issue_state as a deliberate divergence — the "
        "exact silence-as-verdict class the file rails against."
    ),
}

def test_sweep_zero_claim_summary_is_byte_identical(scratch, run_tool):
    """The zero-claim summary must be byte-identical — the port reproduces it.

    This WAS a recorded divergence: the bash's embedded python `sys.exit(0)`s
    BEFORE printing its S (summary) row, so `$counts` is empty and the verdict
    reads '( = claim rows, open tokens, closed tokens, unresolvable tokens).'
    — the four numbers are simply ABSENT. An earlier draft of the port printed
    the real '0 0 0 0' and called it a cosmetic improvement.

    That improvement was WITHDRAWN. The port's contract is byte identity with
    the tool it replaces: a line that reads differently is a line a caller (or
    a cron) can no longer grep for, and a "harmless" divergence in the port is
    indistinguishable from a real one to everything downstream. So the port now
    reproduces the bash's exact text and this leg PINS it.

    The bash line is genuinely WRONG (a population verdict with no population),
    and that is a real defect — but it belongs to the BASH, to be fixed there
    as its own change, not silently patched inside the replacement tool where
    no one would see it. Flagged, not papered over.
    """
    root = str(scratch.path / "parity" / "zero-claim-byte-identical")
    bash, py = run_pair(root, ["sweep-closed-claims", "--dry-run"], run_tool)

    assert bash[0] == py[0] == 0, "rc must agree"
    assert bash[3] == py[3], "the ledger must be untouched by a dry run"
    # The bash omits the counts; the port must omit them the SAME WAY.
    assert "( = claim rows" in bash[1], (
        "the bash no longer omits the counts — re-derive the expected text: %r"
        % bash[1])
    assert bash[1] == py[1], (
        "the zero-claim summary diverged:\n  bash=%r\n  py  =%r"
        % (bash[1], py[1]))

def test_divergence_sweep_probe_failure_stderr(scratch, run_tool):
    """PIN the deliberate stderr addition on a failed gh probe."""
    root = str(scratch.path / "parity" / "divergence-probe-fail")
    bash, py = run_pair(root, ["sweep-closed-claims"], run_tool,
                        rows=CLAIM_ROWS, gh="fail")

    assert bash[0] == py[0] == 3, (
        "rc must agree (3 = the scan failed) — got bash=%r py=%r"
        % (bash[0], py[0]))
    assert bash[3] == py[3], "a failed probe must not write a row"
    # The bash's single line must be present VERBATIM in the Python's stderr.
    final = "oc-ledger: sweep-closed-claims: scan failed (rc 4)"
    assert final in bash[2]
    assert final in py[2], (
        "the Python lost the bash's final line: %r" % (py[2],))
    # And the Python's addition is exactly the gh diagnostic it documents.
    assert "gh issue list --repo" in py[2], (
        "the documented gh diagnostic is gone; KNOWN_DIVERGENCES is stale: %r"
        % (py[2],))
    assert "gh issue list --repo" not in bash[2], (
        "the bash now prints the probe diagnostic too; KNOWN_DIVERGENCES is "
        "stale: %r" % (bash[2],))


# ---------------------------------------------------------------------------
# the four semantics that must survive the port — proved on the PORT, not the
# bash, because after the flip the Python is the only tool left
# ---------------------------------------------------------------------------
def test_append_is_a_true_append_not_a_rewrite(scratch, run_tool):
    """Spec trap 2: one row on the END grows the file by one line + fsync.

    Proved by inode: a wholesale rewrite goes through a temp + ``os.replace``
    and lands on a NEW inode, so the inode surviving is the difference between
    an append and a 2.8 MB rewrite.
    """
    root = str(scratch.path / "parity" / "append-inode")
    state, _skill, env = build_fixture(root)
    ledger = os.path.join(state, "events.jsonl")
    before = os.stat(ledger)
    with open(ledger, "rb") as fh:
        prefix = fh.read()

    res = run_tool([sys.executable, str(PY_TOOL), "stamp", "note", "one row"],
                   timeout=60, env=env)
    assert res.rc == 0, res.err

    after = os.stat(ledger)
    with open(ledger, "rb") as fh:
        body = fh.read()
    assert after.st_ino == before.st_ino, (
        "the append replaced the inode — that is a rewrite, not an append")
    assert body.startswith(prefix), "the existing bytes were not preserved"
    assert body.count(b"\n") == prefix.count(b"\n") + 1, (
        "exactly one line should have been added")


def test_malformed_ledger_is_refused_without_being_touched(scratch, run_tool):
    """Spec trap 1 (the destructive half): a corrupt row RAISES, never skips.

    ``migrate`` rewrites in place, so a port that skipped a bad line would
    silently DROP it from the new record — a corrupt row becoming a missing
    row. The refusal must also leave the source byte-identical.
    """
    root = str(scratch.path / "parity" / "migrate-corrupt")
    state, _skill, env = build_fixture(root, legacy=True,
                                       src_text='{"events":[{"n":1}]}\n{oops')
    src = os.path.join(state, "workers-ledger.json")
    before = open(src, "rb").read()

    res = run_tool([sys.executable, str(PY_TOOL), "migrate", "--to", "jsonl"],
                   timeout=60, env=env)
    assert res.rc == 3, "a malformed source must refuse rc 3, got %r: %r" % (
        res.rc, res.err)
    assert open(src, "rb").read() == before, "the source was modified"
    assert not os.path.exists(os.path.join(state, "events.jsonl")), (
        "a refused migration installed a record anyway")


def test_migrate_force_does_not_leave_the_old_record_installed(scratch,
                                                               run_tool):
    """``--force`` replaces a live record WHOLESALE — no merge, no leftovers.

    The dangerous failure mode for an in-place rewrite is a partial install:
    events replaced while workers.json still describes the OLD population. This
    leg pins both files to the SOURCE's content.
    """
    root = str(scratch.path / "parity" / "migrate-force")
    state, _skill, env = build_fixture(
        root, legacy=True,
        rows=[{"n": 1, "kind": "note", "what": "legacy only"}])
    # Pre-existing live record that --force must overwrite.
    with open(os.path.join(state, "events.jsonl"), "w",
              encoding="utf-8") as fh:
        fh.write('{"n": 99, "kind": "note", "what": "stale live row"}\n')

    res = run_tool([sys.executable, str(PY_TOOL), "migrate", "--to", "jsonl",
                    "--force"], timeout=60, env=env)
    assert res.rc == 0, res.err
    rows = [json.loads(line) for line in
            open(os.path.join(state, "events.jsonl"),
                 encoding="utf-8").read().splitlines() if line.strip()]
    assert [row["n"] for row in rows] == [1], (
        "the stale live row survived --force: %r" % (rows,))
    workers = json.load(open(os.path.join(state, "workers.json"),
                             encoding="utf-8"))
    assert "events" not in workers, (
        "workers.json still carries the events array: %r" % (workers,))


def test_never_spawns_a_child_while_holding_the_lock(scratch, run_tool):
    """Spec trap 3: acquire -> pure Python -> release -> THEN git.

    A ``stamp`` whose state repo cannot commit must still exit 0 with the row
    durable: the git tail runs after the lock is released and is never fatal.
    A repo with a broken ``.git`` is the cheapest way to make git fail.
    """
    root = str(scratch.path / "parity" / "git-tail-nonfatal")
    state, _skill, env = build_fixture(root)
    # Corrupt the git dir so every git call fails, but the ledger stays writable.
    shutil.rmtree(os.path.join(state, ".git"))
    with open(os.path.join(state, ".git"), "w", encoding="utf-8") as fh:
        fh.write("gitdir: /nonexistent\n")

    res = run_tool([sys.executable, str(PY_TOOL), "stamp", "note", "durable"],
                   timeout=90, env=env)
    assert res.rc == 0, (
        "a failing git tail must not fail the append: rc=%r err=%r"
        % (res.rc, res.err))
    rows = [json.loads(line) for line in
            open(os.path.join(state, "events.jsonl"),
                 encoding="utf-8").read().splitlines() if line.strip()]
    assert rows[-1]["what"] == "durable", "the row did not land"
