#!/usr/bin/env python3
"""Dynamic-tool bridge: the `oc_questions` tool -> tools/oc-questions (#547).

Reads the caller's params from $OPENCRABS_PARAMS (a JSON file OpenCrabs writes),
builds a strict argv for the CLI, and returns its stdout. No shell is involved:
subprocess is called with an argument list, so no caller value is ever
interpolated into a command line.

Contract:
  in  : {"action": "ask|list|answer|amend|notify|publish|lint|gc", ...}
  out : the CLI's own output (JSON when --json is requested)
  rc  : the CLI's rc, or 2 on a malformed invocation, 4 if params are unreadable

The asking session is NOT normally a parameter: the CLI reads
OPENCRABS_SESSION_ID from the environment, so the return address cannot be typed
wrong. `session` survives only as an override for callers outside a turn.
"""

import glob
import json
import os
import subprocess
import sys

SKILL_ROOT = os.environ.get(
    "OC_QUESTIONS_SKILL_ROOT",
    "/root/.opencrabs/profiles/ops/skills/opencrabs-dev",
)
TIMEOUT = 25


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

ACTIONS = {"ask", "list", "answer", "amend", "notify", "publish", "lint", "gc", "withdraw"}

# verbs that accept --json
JSON_VERBS = {"ask", "list", "answer", "amend", "notify", "publish", "lint", "gc", "withdraw"}

# verb -> (param, CLI flag) for flags that take a value
VALUED = {
    "ask": [("factory", "--factory"), ("session", "--session"),
            ("ttl_days", "--ttl-days"), ("subject", "--subject"),
            ("close_when", "--close-when")],
    "list": [("lane", "--lane"), ("session", "--session")],
    "amend": [("set_id", "--set"), ("qid", "--qid"),
              ("title", "--title"), ("description", "--description"),
              ("recommended", "--recommended")],
    "notify": [("set_id", "--set"), ("lane", "--lane"),
               ("qid", "--qid"), ("mode", "--mode")],
    "publish": [("set_id", "--set"), ("action_url", "--action")],
    "withdraw": [("set_id", "--set"), ("qid", "--qid"), ("text", "--text")],
}
# verb -> (param, CLI flag) for bare boolean flags
BOOLEAN = {
    "ask": [("no_clarify", "--no-clarify"), ("no_publish", "--no-publish")],
    "list": [("all", "--all"), ("quiet", "--quiet")],
    "amend": [("clear_options", "--clear-options")],
    "answer": [("no_publish", "--no-publish")],
    "notify": [("dry_run", "--dry-run")],
    "publish": [("prune", "--prune"), ("rotate", "--rotate")],
    "gc": [("dry_run", "--dry-run")],
    "withdraw": [("no_publish", "--no-publish")],
}

# Params the bridge handles outside VALUED/BOOLEAN, per verb.
SPECIAL = {
    "ask": {"questions"},
    "amend": {"options"},
    "answer": {"set_id", "qid", "choice", "text", "via"},
}
# Consumed by the bridge itself, never forwarded.
CONSUMED = {"action"}


def check_maps():
    """Every verb wired into a map must be reachable through ACTIONS.

    Origin 2026-09-25: `withdraw` was added to JSON_VERBS, VALUED and BOOLEAN
    but not to ACTIONS, so the gate at the top of main() answered
    "unknown action 'withdraw'" rc=2 while three maps said it existed. Same
    shape as the `factory` defect this bridge was fixed for: wired in several
    places, dropped in one. Returns a list of human-readable violations.
    """
    violations = []
    for name, keys in (("VALUED", VALUED), ("BOOLEAN", BOOLEAN), ("SPECIAL", SPECIAL)):
        for verb in sorted(set(keys) - ACTIONS):
            violations.append("%s wires %r but ACTIONS omits it" % (name, verb))
    for verb in sorted(JSON_VERBS - ACTIONS):
        violations.append("JSON_VERBS wires %r but ACTIONS omits it" % verb)
    return violations


def unmapped_params(action, params):
    """Caller-supplied params this verb cannot pass through.

    The bridge builds argv from VALUED/BOOLEAN -- NOT from the caller's params --
    so a param absent from that map is silently DROPPED. That is how `factory`
    went missing: the schema declared it, the caller supplied it, and the map
    never read it, so `ask` failed rc=2 with AND without the param. This check
    makes that class self-diagnosing instead of silent.
    """
    known = {key for key, _ in VALUED.get(action, [])}
    known |= {key for key, _ in BOOLEAN.get(action, [])}
    known |= SPECIAL.get(action, set())
    known |= CONSUMED
    return sorted(
        key for key, value in params.items()
        if key not in known and value not in (None, "", [], False)
    )


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

def build_argv(action, params):
    argv = [action]

    for key, flag in VALUED.get(action, []):
        value = params.get(key)
        if value in (None, "", []):
            continue
        argv += [flag, str(value)]

    for key, flag in BOOLEAN.get(action, []):
        if params.get(key):
            argv.append(flag)

    if action == "ask":
        questions = params.get("questions")
        if not questions:
            return None, "ask requires `questions` (an ordered array of question objects)"
        # The CLI owns the schema; pass it through as JSON rather than
        # re-encoding it into flags, so no field is lost or reordered.
        argv += ["--questions-json", json.dumps(questions, ensure_ascii=False)]

    if action == "amend":
        # --option is REPEATABLE: a list becomes one flag per option.
        options = params.get("options")
        if isinstance(options, list):
            for option in options:
                argv += ["--option", str(option)]

    if action == "answer":
        for key in ("set_id", "qid", "choice"):
            value = params.get(key)
            if value in (None, ""):
                return None, f"answer requires `{key}`"
            argv.append(str(value))
        if params.get("text"):
            argv += ["--text", str(params["text"])]
        if params.get("via"):
            argv += ["--via", str(params["via"])]

    if action in JSON_VERBS:
        argv.append("--json")

    return argv, None

def main(argv):
    global CLI
    CLI, searched = resolve_cli()
    if CLI is None:
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
    if action not in ACTIONS:
        return fail(f"unknown action {action!r}", 2)

    cli_argv, error = build_argv(action, params)
    if error:
        return fail(error, 2)

    for violation in check_maps():
        sys.stderr.write("oc-questions bridge: MAP DEFECT -- %s\n" % violation)

    stray = unmapped_params(action, params)
    if stray:
        sys.stderr.write(
            "oc-questions bridge: WARNING -- %s not passed through for action %r and "
            "DROPPED. The bridge map (VALUED/BOOLEAN), not the schema, decides what "
            "reaches the CLI; if the CLI needs one of these, add it to the map.\n"
            % (", ".join(repr(s) for s in stray), action)
        )

    if not os.path.exists(CLI):
        return fail(f"CLI not found at {CLI}", 4)

    try:
        proc = subprocess.run(
            [CLI] + cli_argv,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return fail(f"{action} exceeded {TIMEOUT}s", 4)

    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
