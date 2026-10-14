# Node 9 — Finish hosted review and refreshed exact-head PR checks, retaining earlier findings

plan: vault-pr
gate: `test -s logs/vault-hosted-final.json && test "$(gh pr view codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault --json headRefOid --jq .headRefOid)" = "$(git rev-parse HEAD)" && gh pr checks codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault`
ctx: docs/release-review.md
