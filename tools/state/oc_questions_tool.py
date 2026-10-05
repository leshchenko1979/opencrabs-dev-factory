#!/usr/bin/env python3
"""Dynamic-tool bridge: the `oc_questions` tool -> tools/state/oc-questions (#547, #709).

Reads the caller's params from $OPENCRABS_PARAMS (a JSON file OpenCrabs writes),
builds a strict argv for the CLI, and returns its stdout. No shell is involved:
subprocess is called with an argument list, so no caller value is ever
interpolated into a command line.

The argv is DERIVED FROM THE CLI ITSELF, not from a map kept here. Until #709
this file carried hand-written VALUED/BOOLEAN tables -- a second, independent
declaration of what the CLI accepts -- and the two drifted. `list` gained
--factory in the CLI and not in the map, so `list factory=X` forwarded nothing,
returned EVERY factory's questions, and read as a filtered answer; `publish`
advertised a set_id the CLI refuses by name. A hand-kept mirror of a parser is a
defect generator, so the mirror is gone: the CLI publishes its own flag schema
(`oc-questions --schema`, from the one FLAG_SPEC table its handlers parse with)
and this bridge reads it. A param the CLI does not declare is now a hard refusal
naming it, never a warning beside a plausible answer.

Contract:
  in  : {"action": "ask|list|answer|amend|notify|publish|lint|gc|withdraw", ...}
  out : the CLI's own output (JSON when --json is requested)
  rc  : the CLI's rc, or 2 on a malformed invocation, 4 if params are unreadable
        or the CLI's schema cannot be read

The asking session is NOT normally a parameter: the CLI reads
OPENCRABS_SESSION_ID from the environment, so the return address cannot be typed
wrong. `session` survives only as an override for callers outside a turn.
"""

import glob
import json
import os
import subprocess
import sys
import time

SKILL_ROOT = os.environ.get(
    "OC_QUESTIONS_SKILL_ROOT",
    "/root/.opencrabs/profiles/ops/skills/opencrabs-dev",
)
TIMEOUT = 25

# Params the bridge consumes itself or wires by hand, so they are never looked
# up as flags. `questions`/`options` are structured payloads the CLI takes as
# JSON / a repeated flag; the rest are positional on their verb (the CLI
# publishes WHICH via `positional_params`, but the VALUES still arrive here).
CONSUMED = {"action"}
STRUCTURED = {"questions", "options"}


def resolve_cli():
    """Locate the CLI, tolerating the tools/ KIND regroup.

    Returns (path, searched). A hardcoded flat path died six times when tools/
    was regrouped, so this resolves instead: the canonical location first, then
    exactly-one glob match under tools/*/. Pre-images (``.pre-``) are excluded
    because a stray copy must never be executed as the tool.

    Never guesses: an ambiguous result returns (None, searched) so the caller
    can fail loudly. Silence here would repeat the defect it exists to prevent.
    """
    preferred = os.path.join(SKILL_ROOT, "tools", "state", "oc-questions")
    searched = [preferred]
    if os.path.isfile(preferred) and os.access(preferred, os.X_OK):
        return preferred, searched

    hits = sorted(
        p
        for p in glob.glob(os.path.join(SKILL_ROOT, "tools", "*", "oc-questions"))
        if ".pre-" not in os.path.basename(p)
    )
    searched.append(os.path.join(SKILL_ROOT, "tools", "*", "oc-questions"))
    if len(hits) == 1:
        return hits[0], searched

    flat = os.path.join(SKILL_ROOT, "tools", "oc-questions")
    searched.append(flat)
    if os.path.isfile(flat):
        return flat, searched

    return None, searched


def read_schema(cli):
    """Ask the CLI what it accepts. Returns (schema, error).

    This is the whole point of #709: the bridge's authority on the flag set is
    the CLI's own parser, read at call time. A CLI that cannot answer is a
    hard stop -- forwarding ANY argv without a schema would re-create the
    silent-drop class this replaced.
    """
    try:
        proc = subprocess.run(
            [cli, "--schema"], capture_output=True, text=True, timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, f"{cli} --schema exceeded {TIMEOUT}s"
    except OSError as exc:
        return None, f"{cli} --schema could not run: {exc}"
    if proc.returncode != 0:
        return None, (
            f"{cli} --schema exited {proc.returncode}: "
            f"{(proc.stderr or proc.stdout or '').strip()[:200]}"
        )
    try:
        schema = json.loads(proc.stdout)
    except ValueError as exc:
        return None, f"{cli} --schema is not JSON: {exc}"
    if not isinstance(schema, dict) or not isinstance(schema.get("verbs"), dict):
        return None, f"{cli} --schema has no verbs table"
    return schema, None


def build_argv(action, params, schema):
    """argv for the CLI, derived from the CLI's published schema.

    Returns (argv, error). Every caller param must be accounted for: it maps to
    a declared flag, is a published positional, or is a structured payload the
    verb is known to take. Anything else is REFUSED BY NAME -- never dropped.
    """
    verbs = schema.get("verbs") or {}
    spec = verbs.get(action)
    if not isinstance(spec, dict):
        return None, (
            f"the CLI does not declare action {action!r}; it declares "
            f"{', '.join(sorted(verbs)) or '(none)'}"
        )

    # param -> flag MAPS, straight from the CLI. A bare flag list is not
    # enough: `set_id` -> `--set` is not recoverable by any dash rule, and
    # guessing it is how a caller's param goes missing (#709).
    valued = dict(spec.get("valued") or {})
    boolean = dict(spec.get("boolean") or {})
    positional = [
        entry for entry in (spec.get("positional_params") or [])
        if isinstance(entry, dict) and entry.get("name")
    ]
    pos_names = {entry["name"] for entry in positional}

    argv = [action]
    strays = []

    for key, value in params.items():
        if key in CONSUMED or key in STRUCTURED or key in pos_names:
            continue
        if value in (None, "", [], False):
            continue
        if key in valued:
            argv += [valued[key], str(value)]
            continue
        if key in boolean:
            if value:
                argv.append(boolean[key])
            continue
        strays.append(key)

    if strays:
        return None, (
            "%s does not accept %s: the CLI declares %s. The bridge derives its "
            "argv from the CLI's own schema, so a param the CLI does not "
            "declare is REFUSED rather than silently dropped (#709)."
            % (
                action,
                ", ".join(repr(s) for s in sorted(strays)),
                ", ".join(sorted(set(valued) | set(boolean))) or "(no params)",
            )
        )

    if action == "ask":
        questions = params.get("questions")
        if not questions:
            return None, "ask requires `questions` (an ordered array of question objects)"
        # The CLI owns the schema; pass it through as JSON rather than
        # re-encoding it into flags, so no field is lost or reordered.
        argv += ["--questions-json", json.dumps(questions, ensure_ascii=False)]

    if action == "amend":
        # --option is REPEATABLE: a list becomes one flag per option. It is in
        # the declared valued set, so the generic loop skipped it only because
        # a list cannot be str()'d meaningfully -- this is where it lands.
        options = params.get("options")
        if isinstance(options, list):
            for option in options:
                argv += ["--option", str(option)]

    # Positionals in the order the CLI published them; `required` is the CLI's
    # own declaration, not a guess made here.
    for entry in positional:
        value = params.get(entry["name"])
        if value in (None, ""):
            if entry.get("required"):
                return None, f"{action} requires `{entry['name']}`"
            continue
        argv.append(str(value))

    argv.append("--json")
    return argv, None


def store_state(path):
    """(exists, mtime_ns, size) for the register, or None if unreadable."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (True, stat.st_mtime_ns, stat.st_size)


def settle_report(action, store, before, after):
    """Did a timed-out invocation settle a write? (#709)

    A timeout that fires OVER a completed write is the inverse of the usual
    case: the operation succeeded and the caller was told it failed. The
    register is written tmp -> os.replace, so an mtime/size change across the
    call is a write that LANDED. Reported as settled with the un-run step
    named, so a retry cannot duplicate an amend that already applied.
    """
    report = {"error": f"{action} exceeded {TIMEOUT}s", "settled": False,
              "store": store}
    if before is not None and after is not None and before != after:
        report["settled"] = True
        report["detail"] = (
            "the register was rewritten during this call (mtime/size changed), "
            "so the store mutation LANDED even though the CLI did not return "
            "in time; only the follow-up step (page publish / notify) is "
            "unconfirmed. Do NOT retry the mutation blind."
        )
    else:
        report["detail"] = (
            "the register is unchanged, so the operation did not settle a "
            "write; a retry is safe."
        )
    return report


def fail(message, rc):
    print(json.dumps({"error": message}, ensure_ascii=False))
    return rc


def load_params(argv):
    path = None
    if "--params-file" in argv:
        index = argv.index("--params-file")
        if index + 1 < len(argv):
            path = argv[index + 1]
    if path is None:
        path = os.environ.get("OPENCRABS_PARAMS")
    if not path:
        return None, "no params supplied: pass --params-file or set OPENCRABS_PARAMS"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle) or {}, None
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller verbatim
        return None, f"params unreadable: {exc}"


def main(argv):
    cli, searched = resolve_cli()
    if cli is None:
        sys.stderr.write(
            "oc_questions bridge: the CLI could not be located. Searched:\n"
            + "".join("  - %s\n" % p for p in searched)
            + "Set OC_QUESTIONS_SKILL_ROOT, or the tools/ tree was regrouped "
            "again -- repoint resolve_cli().\n"
        )
        return 4

    params, error = load_params(argv)
    if error:
        return fail(error, 4)

    action = str(params.get("action") or "").strip()
    if not action:
        return fail("`action` is required", 2)

    # The CLI is the authority on what it accepts (#709). A schema we cannot
    # read is a hard stop: forwarding argv without it would re-create the
    # silent-drop class this replaced.
    schema, error = read_schema(cli)
    if error:
        return fail(f"cannot read the CLI schema: {error}", 4)

    cli_argv, error = build_argv(action, params, schema)
    if error:
        return fail(error, 2)

    store = schema.get("store") or ""
    before = store_state(store) if store else None
    started = time.time()

    try:
        proc = subprocess.run(
            [cli] + cli_argv,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        after = store_state(store) if store else None
        report = settle_report(action, store, before, after)
        report["elapsed"] = round(time.time() - started, 2)
        print(json.dumps(report, ensure_ascii=False))
        return 4

    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


def _selftest():
    """#709 regression harness: the bridge must derive its argv from the CLI.

    Runs against a FIXTURE CLI in a temp tree, so it never touches the real
    register and needs no network. Each case is one of the three silent-failure
    shapes the issue recorded.
    """
    import importlib.util
    import shutil
    import tempfile

    me = os.path.abspath(__file__)
    spec = importlib.util.spec_from_file_location("ocq_bridge", me)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    root = tempfile.mkdtemp(prefix="ocq-bridge-selftest.")
    passed = failed = 0

    def chk(cond, label):
        nonlocal passed, failed
        if cond:
            passed += 1
            print("  ok   %s" % label)
        else:
            failed += 1
            print("  FAIL %s" % label)

    try:
        tool_dir = os.path.join(root, "tools", "state")
        os.makedirs(tool_dir, exist_ok=True)
        fixture = os.path.join(tool_dir, "oc-questions")
        with open(fixture, "w", encoding="utf-8") as fh:
            fh.write(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "SCHEMA = {'prog': 'oc-questions', 'version': '0', 'verbs': {\n"
                "  'list': {'valued': {'lane': '--lane', 'session': '--session',\n"
                "                      'factory': '--factory'},\n"
                "           'boolean': {'json': '--json', 'all': '--all',\n"
                "                       'quiet': '--quiet'},\n"
                "           'positional': 'none', 'positional_params': []},\n"
                "  'publish': {'valued': {'action': '--action'},\n"
                "              'boolean': {'json': '--json', 'prune': '--prune'},\n"
                "              'positional': 'none', 'positional_params': []},\n"
                "  'amend': {'valued': {'set_id': '--set', 'qid': '--qid',\n"
                "                       'option': '--option'},\n"
                "            'boolean': {'json': '--json'},\n"
                "            'positional': 'none', 'positional_params': []},\n"
                "  'answer': {'valued': {'text': '--text'},\n"
                "             'boolean': {'json': '--json'},\n"
                "             'positional': '<set-id> <qid> [choice]',\n"
                "             'positional_params': [\n"
                "                 {'name': 'set_id', 'required': True},\n"
                "                 {'name': 'qid', 'required': True},\n"
                "                 {'name': 'choice', 'required': False}]}},\n"
                "  'store': os.path.join(os.path.dirname(__file__), 'open.json')}\n"
                "if '--schema' in sys.argv:\n"
                "    print(json.dumps(SCHEMA)); sys.exit(0)\n"
                "rec = os.environ.get('OCQ_FIXTURE_RECORD')\n"
                "if rec:\n"
                "    with open(rec, 'a', encoding='utf-8') as fh:\n"
                "        fh.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "print(json.dumps({'argv': sys.argv[1:]})); sys.exit(0)\n"
            )
        os.chmod(fixture, 0o755)

        schema, err = mod.read_schema(fixture)
        chk(err is None and isinstance(schema, dict), "read_schema reads the fixture")
        chk(schema["verbs"]["list"]["valued"] ==
            {"lane": "--lane", "session": "--session", "factory": "--factory"},
            "read_schema preserves the CLI's own param->flag map")

        # (1) the dropped param: `factory` must reach the CLI, not be warned away.
        argv, err = mod.build_argv("list", {"action": "list", "factory": "f-a"}, schema)
        chk(err is None and argv == ["list", "--factory", "f-a", "--json"],
            "list factory=X forwards --factory (#709 shape 1)")

        # (2) a param the CLI does not declare is a HARD refusal naming it.
        argv, err = mod.build_argv("list", {"action": "list", "mode": "x"}, schema)
        chk(argv is None and err and "'mode'" in err,
            "an undeclared param is refused BY NAME, not dropped (#709 shape 1)")
        argv, err = mod.build_argv("publish", {"action": "publish", "set_id": "s"}, schema)
        chk(argv is None and err and "'set_id'" in err,
            "publish set_id is refused, not forwarded as --set (#709 shape 2)")

        # repeatable + positional wiring still lands.
        argv, err = mod.build_argv(
            "amend", {"action": "amend", "set_id": "s", "qid": "q1",
                      "options": ["a", "b"]}, schema)
        chk(err is None and argv == ["amend", "--set", "s", "--qid", "q1",
                                     "--option", "a", "--option", "b", "--json"],
            "amend forwards repeatable --option and its valued flags")
        argv, err = mod.build_argv(
            "answer", {"action": "answer", "set_id": "s", "qid": "q1",
                       "choice": "0"}, schema)
        chk(err is None and argv == ["answer", "s", "q1", "0", "--json"],
            "answer wires its published positional_params + choice")
        argv, err = mod.build_argv("answer", {"action": "answer", "set_id": "s"}, schema)
        chk(argv is None and err and "qid" in err,
            "answer refuses a missing required positional")

        # (3) a timeout over a settled write is reported as SETTLED.
        store = os.path.join(root, "open.json")
        with open(store, "w", encoding="utf-8") as fh:
            fh.write("{}")
        before = mod.store_state(store)
        with open(store, "w", encoding="utf-8") as fh:
            fh.write('{"sets": []}')
        after = mod.store_state(store)
        rep = mod.settle_report("amend", store, before, after)
        chk(rep["settled"] is True and "LANDED" in rep["detail"],
            "a write that landed under a timeout reads settled=True (#709 shape 3)")
        rep = mod.settle_report("amend", store, after, after)
        chk(rep["settled"] is False and "retry is safe" in rep["detail"],
            "an unsettled timeout reads settled=False (retry safe)")

        # end-to-end through main(): the fixture records the argv it received.
        record = os.path.join(root, "argv.jsonl")
        params_file = os.path.join(root, "params.json")
        with open(params_file, "w", encoding="utf-8") as fh:
            json.dump({"action": "list", "factory": "f-a"}, fh)
        saved_root = os.environ.get("OC_QUESTIONS_SKILL_ROOT")
        saved_rec = os.environ.get("OCQ_FIXTURE_RECORD")
        saved_const = mod.SKILL_ROOT
        # SKILL_ROOT is resolved at import time, so the env var alone would
        # leave main() pointed at the REAL CLI. Patch the module constant the
        # resolver actually reads -- otherwise this leg would silently drive
        # the live register instead of the fixture.
        os.environ["OC_QUESTIONS_SKILL_ROOT"] = root
        os.environ["OCQ_FIXTURE_RECORD"] = record
        mod.SKILL_ROOT = root
        try:
            rc = mod.main(["--params-file", params_file])
        finally:
            mod.SKILL_ROOT = saved_const
            if saved_root is None:
                os.environ.pop("OC_QUESTIONS_SKILL_ROOT", None)
            else:
                os.environ["OC_QUESTIONS_SKILL_ROOT"] = saved_root
            if saved_rec is None:
                os.environ.pop("OCQ_FIXTURE_RECORD", None)
            else:
                os.environ["OCQ_FIXTURE_RECORD"] = saved_rec
        got = []
        if os.path.isfile(record):
            with open(record, encoding="utf-8") as fh:
                got = [json.loads(line) for line in fh if line.strip()]
        chk(rc == 0 and got and got[-1] == ["list", "--factory", "f-a", "--json"],
            "end-to-end: main() drives the CLI with --factory (rc=%s, argv=%r)"
            % (rc, got[-1] if got else None))

        # a CLI whose schema cannot be read is a hard stop, never a blind forward.
        broken = os.path.join(root, "broken-oc-questions")
        with open(broken, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 7\n")
        os.chmod(broken, 0o755)
        _s, err = mod.read_schema(broken)
        chk(err is not None and "exited 7" in err,
            "an unreadable schema is a hard stop naming the exit code")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("oc_questions_tool bridge selftest: %d passed, %d failed"
          % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(_selftest())
    sys.exit(main(sys.argv[1:]))

