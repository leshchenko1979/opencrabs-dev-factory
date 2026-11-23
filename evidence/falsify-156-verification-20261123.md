# falsify-156-measurements — child agent 597ecc63

(read-only child spawned by HQ lane 0117dd29, completed 2026-11-23T10:38:39.068026791+00:00; report verbatim)

---

**Compaction roast:** I lost the memory of reading a 426 KB file and now get to re-read it in 14 KB dribbles like a man rebuilding a cathedral from photographs of the rubble. Four compactions, one shell-free sandbox, and my reward is fetching the same bytes twice. Wonderful.

---

# Verification report — ledger / swap-stage defect @ `9d09c9f5`

**Method caveat, stated up front (this bounds every claim below).** This session has **no shell** (read-restricted registry #1173), so the mandated `git show HEAD:<path>` / `git grep -n PATTERN HEAD -- path` were **not executed**. Every byte below was read from the GitHub mirror at the exact commit `9d09c9f524256afa7cb8c11e766618a39197d502` (`GET api.github.com/repos/leshchenko1979/opencrabs-dev-factory/commits/main` → that sha), via `raw.githubusercontent.com` byte ranges. Content is byte-identical and line numbers were pinned against the blob HTML (`data-line-number`). **No `git grep` census exists** — §Q4 is therefore structural, not exhaustive, and I say so there.

---

## Q1 — Ordinal compatibility (`n` allocation)

**Not compatible in JSONL mode. Two independent counters over two different files.**

- `tools/lib/oc-deploy-lib.sh:562-574` — `ledger_stamp()`, whole body, **no mode branch anywhere**:
```bash
ledger_stamp() { # $1=by  $2=what  $3=kind
  [ "$3" = "swap-result" ] || { echo "oc-deploy: ledger_stamp kind must be swap-result (enum write-side guard, v0.4.77)" >&2; return 2; }
  (
    flock -x 9
    local n tmp
    n="$(jq '[.events[].n] | max // 0' "$LEDGER" 2>/dev/null || echo 0)"
    tmp="$(mktemp)" || exit 4
    jq --argjson n "$((n+1))" --arg t "$(date -u +%FT%TZ)" --arg by "$1" \
       --arg what "$2" --arg kind "$3" \
       '.events += [{n:$n, t:$t, by:$by, what:$what, kind:$kind}]' \
       "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
  ) 9>"$LEDGER.lock"
}
```
  → `n` is `max` over **`$LEDGER` = the view**, never `events.jsonl`.

- `tools/state/oc-ledger`, `max_n()` — reads a **different** file depending on mode:
```bash
max_n() {
  if _jsonl_mode; then
    jq -s '([.[] | .n // 0] | max // 0)' "$(_JSONL_EVENTS)" 2>/dev/null || echo 0
    return 0
  fi
  jq '([.events[]? | .n // 0] | max // 0)' "$LEDGER"
}
```
- `oc-ledger`, `_stamp_locked()` — allocates from it: `local n t; n=$(( $(max_n) + 1 )); t="$(now_iso)"`.

**The author's own comment condemns the view-max** (oc-ledger, above `max_n`):
> `# #149: in JSONL mode 'n' is allocated from the RECORD, never from the view. The view is gitignored once cut over, so a fresh clone has none — and a max_n() that read a missing view would answer 0 and hand the next writer n=1, colliding with every live row.`

`oc-deploy-lib.sh:567` **is** that "next writer". It is not routed through `max_n()` and cannot be.

- Two further ordinal hazards in `oc-deploy-lib.sh:567`, both silent:
  - `.events` absent → `[.events[].n]` raises *Cannot iterate over null* → `2>/dev/null` swallows it → `|| echo 0` → `n=1`. Every swap after that starts at 1 again.
  - `flock -x 9` locks `"$LEDGER.lock"`; oc-ledger locks the same name — **but only if both tools canonicalise the path identically. They do not (§Q2).** Two different lock files = no mutual exclusion.

---

## Q2 — Legacy-mode path resolution

- `--ledger` is real, and it is a **global** flag consumed before the verb (`oc-ledger`, `parse_global`):
```bash
--ledger) LEDGER="${2:-}"; [ -n "$LEDGER" ] || die 2 "--ledger needs a path"; shift 2 ;;
...
[ -n "$LEDGER" ] || LEDGER="${OC_LEDGER:-}"
[ -n "$LEDGER" ] || { [ -n "${OC_DEPLOY_STATE_DIR:-}" ] && LEDGER="$OC_DEPLOY_STATE_DIR/workers-ledger.json"; }
[ -n "$LEDGER" ] || LEDGER="$STATE_DIR_DEFAULT/workers-ledger.json"
```
- `oc-deploy-lib.sh:53-63` resolves the **same default filename** but then **canonicalises** it:
```bash
[ -f "$LEDGER" ] && LEDGER="$(readlink -f "$LEDGER")"
```
- **Divergence:** `oc-ledger` never calls `readlink -f`. `STATE_DIR() { _oc_dirname "$LEDGER"; }` is a purely **lexical** parent-strip. So on any symlinked, relative, or trailing-slash path the two tools compute **different state dirs** — different `events.jsonl`, different `$LEDGER.lock`, different `git -C "$sd"` repo. Both tools agree on the *default* path and disagree on *identity*.
- `oc-deploy-lib.sh` accepts **no** `--ledger` flag at all (env/defaults only), so the override surfaces are asymmetric too.

---

## Q3 — Stage surface

- `oc-deploy-lib.sh`, `stage()` (block header `stage reader + shadow log (moved verbatim: 585-590)`), reads the **view**:
```bash
stage() { jq -r '.meta.oc_deploy_stage // "S0"' "$LEDGER" 2>/dev/null || echo S0; }
```
- `oc-ledger`, `_git_state_commit_now()` — the only place in either tool that knows the mode exists:
```bash
  if _jsonl_mode; then
    git -C "$sd" add events.jsonl workers.json 2>/dev/null || stage_ok=0
  else
    git -C "$sd" add "${LEDGER##*/}" 2>/dev/null || stage_ok=0
  fi
```
  with its own rationale inline: `# #149: in JSONL mode the RECORD is what gets committed. Staging only 'basename "$LEDGER"' would stage the gitignored view and commit NOTHING — a state commit that reports ok with an empty tree`.
- `oc-ledger` declares the view **non-authoritative**, verbatim (`# ---- #149: JSONL record + materialized view ----`):
> `workers-ledger.json becomes a MATERIALIZED VIEW regenerated from those two, existing only so the 25 legacy consumers keep working — never authoritative.`

**Consequence the bytes force:** in JSONL mode `oc-deploy-lib.sh` writes its `swap-result` row into a file that is (a) gitignored, (b) staged by nothing, and (c) **regenerated from `events.jsonl` + `workers.json` on the next oc-ledger mutation**. The swap row is not misnumbered — it is **erased**. `oc-swap` inherits this: its header states ledger stamping is `SHARED and live[s] in tools/lib/oc-deploy-lib.sh`.

---

## Q4 — Writer census

**Not executable here.** `git grep` needs a shell I do not have, and no unauthenticated code-search route exists (`api.github.com/search/code` requires auth). What the bytes *do* establish:

Production code paths that produce `workers-ledger.json` content — **two, not one**:
1. `tools/lib/oc-deploy-lib.sh:562-574` `ledger_stamp()` — `jq '.events += …'` → `mv` onto `$LEDGER`. **No JSONL branch.** (`stage()` also *reads* it.)
2. `tools/state/oc-ledger` `_stamp_locked()` → `atomic_jq '.events += …'` — in JSONL mode this lands in `events.jsonl`, then `ledger_write_view "$next"` **rewrites the view**; in legacy mode it rewrites `$LEDGER` wholesale.

Stager (not a content writer): `oc-ledger` `_git_state_commit_now()` — `events.jsonl workers.json` vs `${LEDGER##*/}`.

Fixture/test writers (none named `workers-ledger.json`): `tools/harvest/oc-harvest-dispatch` `cmd_selftest` — `local mode_ledger="$st_dir/ledger-mode.json"` with `with_modes()` doing `jq '.events += [{"n":$n,…}]'`; plus heredoc fixtures `ledger-spread.json`, `role-ledger.json`, `fence-ledger.json`, `diff-ledger.json`, `mock_ledger`.

So the honest census statement is: **≥2 production writers of the view, and they disagree about what the file is.** A count of "1 production writer" is wrong on the bytes I read.

---

## Q5 — The write path

- `oc-ledger`, `atomic_jq` (the record write) — append when the mutation pushed exactly one event, else rewrite:
```bash
  if [ -s "$app" ]; then
    cat "$app" >> "$ev" || { rm -f "$base" "$next" "$app" "$tmp"; _OC_TMP=""; return 4; }
    sync -f "$ev" 2>/dev/null || sync 2>/dev/null || true
  else
    ... mv "$ev.tmp.$$" "$ev" ...
  fi
  ...
  ledger_write_view "$next" || { ... return 4; }
```
  with the ordering rule stated inline: `# The RECORD first: if we die after this, events.jsonl is already right and the view is merely stale (the next write regenerates it). Fail toward the record, never toward the view.`
- `oc-deploy-lib.sh:569-572` — the swap's path is the **opposite**: `mktemp` → full-file `jq` transform → `mv` onto the view. No append, no `sync`, no record, no view regeneration. It is a *writer of a derived artefact that does not know it is derived*.

---

## Claims adjudicated

| # | Claim | Verdict |
|---|---|---|
| 1 | `ledger_stamp` uses `jq '.events += […]'` | **CONFIRMED** — `oc-deploy-lib.sh:571`, quoted verbatim above. (The same idiom also appears in `oc-ledger` `_stamp_locked`, which is why the shape looks familiar and is *not* the defect.) |
| 2 | The view-max `n` stays correct | **FALSIFIED** (JSONL mode). `oc-deploy-lib.sh:567` maxes over the view; `oc-ledger` maxes over `events.jsonl`; the view is documented as `never authoritative` and `regenerated`. Two counters, one of them over a cache. Also: absent `.events` silently yields `n=1`. |
| 3 | `oc-ledger` accepts `--ledger` | **CONFIRMED** — `parse_global`, `--ledger) LEDGER="${2:-}" … die 2 "--ledger needs a path"`. |
| 4 | `STATE_DIR` is pure-bash, byte-identical to `dirname` | **CONFIRMED as stated, but misleading.** `_oc_dirname()` is pure-bash and the tool's own comment asserts byte-identity with coreutils on every path shape (`trailing slashes collapsed, no-slash -> ".", "/x" -> "/"`). **However** `STATE_DIR()` is *not* equivalent to `oc-deploy-lib`'s resolved dirname, because deploy-lib additionally does `readlink -f` (`:53-63`) and oc-ledger does not. Byte-identical to `dirname` ≠ identical to the other tool. |
| 5 | The grep baseline "IS SIX" = 1 `deploy-lib:571` + 1 `oc-harvest-dispatch:2168` mock `ledger-mode.json` + 4 untracked `.bak` husks | **FALSIFIED as a `git grep` baseline, twice over.** (a) Four of the six are **untracked** — untracked files are invisible to `git grep HEAD` *by construction*; a git-grep census cannot contain them, so the arithmetic cannot describe the command it claims to describe. (b) The fixture at `oc-harvest-dispatch` writes **`ledger-mode.json`** (`local mode_ledger="$st_dir/ledger-mode.json"`) — that line does **not** match a `workers-ledger.json` grep; it matches `\.events \+=`. (c) The census also omits `oc-ledger` itself, which is the second production producer of the view (§Q4). |

---

## Bottom line

The defect is real and **worse than an ordinal collision**. In JSONL mode there are two write paths to one filename: `oc-ledger` treats `workers-ledger.json` as a regenerable view over `events.jsonl`+`workers.json`, and `oc-deploy-lib.sh:562-574` treats it as the authoritative record. Because `ledger_write_view` rebuilds the view from the record, a `swap-result` row stamped by the swap leg **does not survive the next `oc-ledger` mutation** — the deploy trail is not renumbered, it is deleted, silently, with no error on either side. The ordinal mismatch at `:567` is the *first* symptom a reader would notice; the data loss is the one that matters.

Nothing was fixed, edited, or written. No `session_notify`, no options raised.