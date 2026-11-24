# session-notify — tool mechanics (split out of SKILL.md, v0.4.262)

**Owns:** the `session_notify` TOOL's delivery mechanics — what the call does, what it
cannot do, and how to read its verdict. The delivery LAW (which mode, what ack, the
escalation tier) is canonical at `fleet-directives.md` §Cross-lane message delivery
discipline — **not restated here.**

Re-homed from `SKILL.md §session_notify mechanics` by cycle `20260925-c24` lens B (B-H2):
the always-loaded router carried the notify procedure while its own mode-table bullet said
*"pointer only, no second copy"* — and carried a second copy.

## Tool mechanics (upstream #1203, commit 13a24f25)

- Same-process only: pushes into a LIVE session's queue on THIS box. Target must
  have messaged since boot; dead/cross-instance targets error → fall back to
  `a2a_send`, else list UNREACHABLE in the report.
- DELIVERY ≠ QUEUE ACCEPTANCE: a ping counts as delivered
  ONLY with post-ping proof — same-turn live roster check (`session_search`),
  target PINGED-WOKEN (`last_active` > ping time) or PINGED-SILENT. Ledger
  entries saying "pinged" without wake evidence are forbidden (all roles).
- Sender identity is mechanical — deliveries arrive prefixed
  `[session-notify from=<uuid>]`; replies route back with `target_session = from`.
  Neither role can forge or strip identity.
- Delivery drains at the target's next tool-loop boundary and wakes idle
  sessions — no polling anywhere.

- **RATE LIMITS ARE ENFORCED PER SURFACE (owner ruling 2026-09-08, research-backed —
  `governor.rs`):** Telegram's per-chat flood limits are enforced **per surface** —
  1 msg/s per chat, 20 msg/min per group, ~20 edits/min per group — so a window
  declared on the rich arm does NOT throttle the send arm's separate budget. On a
  429 the daemon pauses **ONLY the offending arm**, because the offending arm IS the
  evidence. A proposal to bound the **SUM** of the buckets (an aggregate per-chat
  gate) would REVERSE this ruling — the buckets are deliberately independent. Fork
  issue #580 owns that open question; until it rules, do not add one.
- Refusal handling: **the `session_notify` path never refuses.** `interrupt` is
  hardcoded true on this tool's route (`src/brain/tools/subagent/notify.rs:371`),
  so the mid-turn gate (`src/brain/agent/service/session_routes.rs:336`) is
  bypassed and a busy target QUEUES the message for its next tool-loop boundary —
  send `turn-end` (the default) and do nothing else. `interrupt: true` is a
  legacy alias for the urgent tier (precedence framing, never deferred — but still
  not pre-emption); `now` fails the delivery outright.
  A `no wake observed` confirm verdict MEANS the target is mid-turn — never
  re-send on it. Do NOT generalise this to "there is no refusal path": the
  `Delivery::RefusedInFlight` variant is still constructed and reachable from
  other callers that pass `interrupt=false` (`quiet_delivery.rs:199`,
  `a2a/handler/notify.rs:266`, `cron/scheduler.rs:1174`).
- CLI form carries `--sender "<lane label>" --title "<topic>"` where supported
  (oc-fanout fanout precedent) — the mechanical `from=<uuid>` header is added
  on top and cannot be forged or stripped.
- **`from` is a RETURN ADDRESS only when the sender is a LIVE SESSION (v0.4.243,
  cycle `20260922-c22`).** The identity bullet above holds for a lane-to-lane notify
  and NOT for a notify whose sender is not a session at all — a cron job, a
  fan-out generator, or a tool. There `from` is a SYNTHETIC label naming the
  component that sent it, not a mailbox: a reply addressed to it reaches nothing,
  and a synthetic `from` is WRITE-ONLY. Measured 2026-09-22 (lanes 4b4463d5 and
  a5b34466, converged independently): a lane replying to a cron-originated notify
  was writing into a label. A reply that matters must name the PROCESS OWNER
  session, resolved live, not the `from`.

## Delivery modes

Canonical, with no second copy: **`fleet-directives.md` §Cross-lane message delivery
discipline** — `turn-end` is the default, `quiet` is a deliberate choice, `now` is
RETIRED and hard-errors, and `interrupt` is the URGENT tier (same boundary, precedence
framing, never pre-emption).
