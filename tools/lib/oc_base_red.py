"""oc_base_red — ONE owner of the BASE-RED marker store (#630).

A BASE-RED marker records that a fork gate run FAILED on a file OUTSIDE the
gated PR's own diff: the failure belongs to the BASE the unit is cut from, not
to the unit. `tools/harvest/oc-pr-fault-scope` already DECIDES that
(IN-SCOPE vs BASE-FAULT by failing-files n PR-files); before #630 the decision
was only printed, so nothing a later run could read.

Both ends share this module so the key cannot drift: the WRITER records under
the base sha the unit would be cut from (`oc-wt add`'s default base is
`origin/main`), and the READER (`oc-harvest-census check`) refuses only on an
EXACT sha match. Exact, never ancestor-or-equal: a marker for a superseded base
must not refuse (#630 acceptance criterion 4), so an advanced base is a MISS,
not a hold. That is deliberately fail-open -- a false refusal blocks a clean
unit, and the cost of a miss is a re-run.

Store: <state_dir>/base-red.json -- a TRACKED state-dir class, listed in
`tools/state/oc-ledger`'s STATE_TRACKED_PATHS so the sweeper that carries
`pacemakers-off` carries this too (a class named durable but swept by nothing
is the #508 defect).
"""
import json
import os
import re
import subprocess
import tempfile
import time

STORE_NAME = 'base-red.json'
# Eviction is by count, newest-first. A marker is a claim about ONE base sha and
# goes stale the moment the base advances, so retaining thousands of them buys
# nothing and grows a file every reader parses.
MAX_MARKERS = 200
_SHA40 = re.compile(r'[0-9a-f]{40}')


def store_path(state_dir):
    return os.path.join(state_dir, STORE_NAME) if state_dir else ''


def resolve_base(repo_path, pin=''):
    """The sha of the base a unit would be cut from.

    ONE resolver, because both ends must agree on the key or the reader silently
    never matches the writer -- the drift defect `lib/oc-wt-resolve.sh` was
    created to kill (two private copies of the same guess).

    The pin wins: a full 40-hex sha is used VERBATIM (that is the key form the
    writer records), and a ref is resolved against the repo. With no pin,
    `origin/main` -- the base `oc-wt add` documents as its default -- then
    `main`. Requires <repo>/.git to exist so a stray path cannot walk UP into an
    enclosing repository and return a base the caller never named.

    Returns '' when nothing resolves. The CALLER must DISCLOSE that rather than
    read it as a clean base (fail-open, never fail-silent).
    """
    pin = (pin or '').strip()
    if pin and _SHA40.fullmatch(pin):
        return pin
    if not repo_path or not os.path.exists(os.path.join(repo_path, '.git')):
        return ''
    for ref in ([pin] if pin else ['origin/main', 'main']):
        cp = subprocess.run(['git', '-C', repo_path, 'rev-parse', '--verify',
                             '--quiet', ref], capture_output=True, text=True)
        if cp.returncode == 0 and cp.stdout.strip():
            return cp.stdout.strip()
    return ''


def load(state_dir):
    """Return {sha: record}. A missing or unreadable store is EMPTY, never an
    exception: an unreadable store must not turn into a refusal."""
    path = store_path(state_dir)
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return {}
    markers = data.get('markers') if isinstance(data, dict) else None
    return markers if isinstance(markers, dict) else {}


def lookup(state_dir, sha):
    """The marker for EXACTLY this base sha, or None."""
    if not sha:
        return None
    return load(state_dir).get(sha)


def record(state_dir, sha, **fields):
    """Write the marker for `sha`, merging into the existing store.

    Atomic: written to a temp file in the same directory then renamed, so a
    reader never sees a half-written store (two lanes can write concurrently).
    Returns the stored record.
    """
    path = store_path(state_dir)
    if not path:
        raise ValueError('no state dir')
    os.makedirs(state_dir, exist_ok=True)
    markers = load(state_dir)
    rec = dict(fields)
    rec['sha'] = sha
    rec.setdefault('recorded_at', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    markers[sha] = rec
    if len(markers) > MAX_MARKERS:
        newest = sorted(markers.items(),
                        key=lambda kv: kv[1].get('recorded_at', ''), reverse=True)
        markers = dict(newest[:MAX_MARKERS])
    fd, tmp = tempfile.mkstemp(dir=state_dir, prefix='.base-red.', suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump({'markers': markers}, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, path)
    return rec


def remove(state_dir, sha):
    """Drop the marker for `sha`. Returns True when one was there.

    The escape hatch for a FALSE marker: a base fault fixed without advancing the
    base (or one recorded against the wrong sha) would otherwise refuse a clean
    unit until the base moved. Rewritten through the same atomic path as
    `record`, so a reader never sees a half-written store.
    """
    path = store_path(state_dir)
    if not path or not os.path.exists(path):
        return False
    markers = load(state_dir)
    if sha not in markers:
        return False
    del markers[sha]
    fd, tmp = tempfile.mkstemp(dir=state_dir, prefix='.base-red.', suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump({'markers': markers}, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, path)
    return True


def describe(rec):
    """One-line render of a marker for a refusal/debug message."""
    if not rec:
        return '?'
    files = rec.get('failing_files', []) or []
    tail = ' (+%d more)' % (len(files) - 3) if len(files) > 3 else ''
    return 'run %s, PR #%s, failing %s%s' % (
        rec.get('run', '?'), rec.get('pr', '?'),
        ', '.join(files[:3]) or '?', tail)
