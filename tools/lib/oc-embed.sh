# =============================================================================
# lib/oc-embed.sh — single job-name embed decoder (E2 finding 3, v0.4.72)
# =============================================================================
# Decodes the job-name identity embed from a quick-build run. TWO shapes are in
# the wild: the build-job "(<40-hex>, <features>)" and the gates-job bare
# "(<40-hex>)". TWO functions, ONE home for each predicate:
#   oc_decode_job_embed    -> "sha|features" or empty   (TWO-FIELD ONLY)
#   oc_decode_job_sha_any  -> 40-hex sha or empty        (EITHER shape)
# ONE implementation: oc-job-verify and oc-artifact-verify both had private
# copies that had already drifted (grep vs sed, plus a dead identical fallback
# in oc-job-verify); oc-deploy carried a private any-shape copy from #72 until
# factory #34 moved it here.
#
# Function form so callers keep their own gh/jq plumbing; sourcing guard
# matches lib/oc-log.sh house style.
# =============================================================================

# oc_decode_job_embed <job-name> -> "sha|features" on stdout, empty if none
oc_decode_job_embed() {
  printf '%s\n' "${1:-}" | sed -nE 's/.*\(([0-9a-f]{40}),[[:space:]]*([^)]*)\).*/\1|\2/p'
}

# oc_decode_job_sha_any <job-name> -> 40-hex sha on stdout, empty if none.
# Accepts EITHER job-name shape (fork #72): the build-job embed
# "(<sha>, <features>)" (via oc_decode_job_embed, features dropped) OR the
# gates-job bare form "(<sha>)". ONE implementation — oc-deploy carried a
# private copy of this from #72 until factory #34 moved it here.
#
# NOT a replacement for oc_decode_job_embed: that one stays TWO-FIELD-ONLY and
# its contract is load-bearing — run_built_sha takes the FIRST job name that
# decodes, and the battery asserts the bare form is NOT decodable by it
# (tools/tests/run.sh, section 00b). A caller that needs FEATURES uses
# oc_decode_job_embed; a caller that needs only the sha uses this — a gate-mode
# run has no features in its name at all.
oc_decode_job_sha_any() {
  local s
  s="$(oc_decode_job_embed "${1:-}" 2>/dev/null | cut -d'|' -f1)"
  [ -n "$s" ] && { printf '%s' "$s"; return 0; }
  printf '%s\n' "${1:-}" | sed -nE 's/.*\(([0-9a-f]{40})\).*/\1/p'
}
