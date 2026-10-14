# Node 7 — Open the review PR and verify successful remote CI at the exact final head

plan: vault-pr
gate: `test "$(gh pr view codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault --json headRefOid --jq .headRefOid)" = "$(git rev-parse HEAD)" && gh pr checks codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault`
ctx: docs/release-review.md
