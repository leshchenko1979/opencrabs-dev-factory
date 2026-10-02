# Open Questions — install note

**Audience:** someone standing up the Open Questions register on their own OpenCrabs instance.
**Date:** 2026-10-02 · **Tool version:** 2.0.0

---

## What this is

A register where an agent parks the decisions it is blocked on, renders them as a page you can
open in a browser, and receives your answers back into the asking agent session. The agent asks;
you answer on the page; the answer is delivered to the session that asked.

You need three things: **two files**, **a Node build directory**, and — only if you want an
*agent* to call it as a tool — **the bridge + one config entry**. There is no pip package and no
installer.

---

## 1. Where the code is

| file | path in this repo | blob sha |
|---|---|---|
| CLI | `tools/state/oc-questions` | `6a117817c3d10f16e60351e08fce21a9f0ac012c` |
| renderer | `tools/state/oc-questions-render.mjs` | `3d71b3812242d78a02c2875f728f1c0c13b8dfc6` |
| bridge (agent calls only) | `tools/state/oc_questions_tool.py` | `5b15a6ad554954b181b8e0dae38777828dc4cf30` |

This repository is a working fleet repository, so it carries more than the tool. Clone shallowly,
or fetch just the files you need:

```bash
DEST=~/.opencrabs/profiles/<your-profile>/skills/opencrabs-dev/tools/state
BASE=https://raw.githubusercontent.com/leshchenko1979/opencrabs-skill/main

mkdir -p "$DEST"
curl -fsSL -o "$DEST/oc-questions"            "$BASE/tools/state/oc-questions"
curl -fsSL -o "$DEST/oc-questions-render.mjs" "$BASE/tools/state/oc-questions-render.mjs"
curl -fsSL -o "$DEST/oc_questions_tool.py"    "$BASE/tools/state/oc_questions_tool.py"
chmod +x "$DEST/oc-questions"
```

**The two tool files must keep their names and sit in the same directory.** The CLI looks for the
renderer *beside itself* by deriving the name: `oc-questions` → `oc-questions-render.mjs`. Rename
one and you must rename the other, or the renderer will not be found.

The `+x` is **load-bearing, not cosmetic**: the tool's own selftest re-executes the CLI as a
subprocess for its concurrency leg, and the answer backend can invoke it directly.

---

## 2. Requirements

- **Linux**, **Python 3** (standard library only — nothing to `pip install`)
- **Node.js + npm** (tested on Node `v22.22.3`, npm `10.9.8`) — the page renderer needs them
- An **OpenCrabs profile directory** — the tool derives its own state paths from your profile
  home, so no paths need configuring to get started

---

## 3. The renderer's Node dependencies

The CLI copies the renderer into a **build directory** and runs it there, because ESM resolves a
bare import from the *importing file's* own location. So `node_modules` must live in that build
directory — **not** beside the CLI.

```bash
BUILD=~/.opencrabs/profiles/${OC_PROFILE:-ops}/questions/build
mkdir -p "$BUILD"
cat > "$BUILD/package.json" <<'JSON'
{
  "name": "oc-questions-render",
  "private": true,
  "type": "module",
  "version": "0.0.1",
  "description": "Static renderer for the Open Questions page: json-render spec -> HTML",
  "dependencies": {
    "@json-render/core": "0.21.0",
    "@json-render/react": "0.21.0",
    "react": "19.2.3",
    "react-dom": "19.2.3",
    "zod": "4.5.4"
  }
}
JSON
cd "$BUILD" && npm install
```

> **This is the step people skip, and skipping it produces a silent half-install.** The CLI
> registers questions happily and publishes nothing, because every render exits non-zero for want
> of a module. Nothing warns you: the render fault is reported as a *reason*, and the last good
> page keeps serving. If your page never appears, check this step first.

---

## 4. Verify

```bash
"$DEST/oc-questions" selftest   # scratch store; store, concurrency, renderer, refusal paths
"$DEST/oc-questions" lint       # store + configuration sanity
"$DEST/oc-questions" --help     # the full verb surface
```

The selftest needs `node` and the `node_modules` from step 3 to pass.

---

## 5. Configuration — the parts that are OURS, not yours

Everything has a working default off your own profile home. The first two default to the values
of the instance this tool was extracted from, so **you must change them**:

| variable | default | set it to |
|---|---|---|
| `OC_QUESTIONS_BASE_URL` | `https://questions.l1979.ru` | **your own origin** — otherwise the page URLs it hands out point at someone else's host |
| `OC_QUESTIONS_TRACKER` | `leshchenko1979/opencrabs` | your own issue tracker, `owner/repo` — used by the mechanical-closure check |
| `OC_QUESTIONS_DIR` | `<profile home>/questions` | only if you want the store elsewhere |
| `OC_QUESTIONS_RENDER_DIR` | `<store>/build` | only if you want the build elsewhere |
| `OC_QUESTIONS_DB` | `<profile home>/opencrabs.db` | usually leave alone — it already points at your own instance |
| `OC_QUESTIONS_SKILL_ROOT` | a path on the author's box | **where you unpacked this repo** — the bridge searches it for the CLI |

`OC_QUESTIONS_DB` is worth knowing about: the tool resolves a lane's **display name** from the live
session binding in your instance's database, never from a value the caller supplies. On your own
profile that default is already correct.

---

## 6. Letting an agent call it

Running it from the shell needs nothing more than steps 1–4. To let an **agent** call it, append
`tools/state/tools.toml.example` to your profile's `tools.toml`, replace both placeholder paths
with wherever you put this repository, and reload the tool registry.

The bridge builds a strict argv and calls the CLI with an argument list — **no shell is involved**,
so no caller-supplied value is ever interpolated into a command line. The asking session is read
from the environment (`OPENCRABS_SESSION_ID`), so the return address cannot be typed wrong.

---

## 7. Serving the page — separate from the tool

The tool writes the page **locally**, into `<store>/pages/<token>/`. Making it reachable on the
internet is your own infrastructure, and the tool does not do it.

For reference, the author's arrangement is three pieces: a systemd `.path` unit watching the
store, a oneshot `.service` that rsyncs the pages to a small host, and a web server serving them.
**Without any of that, everything still works** — you just open the page from disk.

---

## 8. Bounds — read before you redistribute

- **htmx is fetched from unpkg at publish time** and vendored into the token directory. With no
  network the page degrades to a plain form: it still works, it just loses the inline swap.
- **Delivery is best-effort and single-shot.** The answer is recorded first, then delivered to the
  asking session. If that delivery fails the answer is still safe and still visible in the
  register — but the lane is not woken. The tool records the outcome per question; nothing retries
  automatically.
- **Nothing tells you your copy is stale.** A copy on disk is a copy nobody compares. Re-pull from
  a newer revision when you want the fixes.
- **The governing contract is not in this repository.** The canon is `docs/instruments/open-questions.md`
  in a private factory repository. `tools/docs/RC-CONTRACT.md` here documents the tool's exit codes
  and behaviour in detail, so you are not blind — but the contract that governs it is out of reach.

---

## Provenance

The canonical source of truth for this tool is the private `agent-factories` repository at
`TEMPLATE/tools/questions`. The copies in this repository are the fleet's distribution form; the
CLI differs from canonical only by the deployment rename (canonical calls the program `questions`,
this fleet calls it `oc-questions`). `tools/docs/vendor-manifest.json` records the exact revision
and each permitted difference, and `tools/audit/oc-vendor-drift` enforces it.

If you edit anything under `tools/state/`, you have made this copy diverge from its source. Record
it in that manifest rather than leaving the divergence unrecorded.
