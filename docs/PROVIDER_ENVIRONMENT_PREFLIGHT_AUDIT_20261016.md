# Public provider transport preflight — 2026-10-16

The history-free release candidate originally exposed a closure error: the
2026-10-15 provider audit imported two untracked experiment-private modules,
whose recursive closure included unreleased request-construction code. The
credential-free Layer A suite did not cover Layer D, so that omission was not
visible until the final five-layer candidate audit.

The release now contains `llm4or/public_antchat_transport.py`, a first-party,
body-free transport identity surface. It binds only the public endpoint,
`DeepSeek-V4-Flash`, concurrency 5, the certifi bundle identity, and verified
TLS-context construction. It contains no request messages, prompt, response
body, API key, private contract, or evaluator-only answer. The private
experiment envelope and its recursive development closure remain outside the
release.

`scripts/verify_provider_environment.py --check` passes with Python 3.10.1 and
certifi 2026.7.22. The machine audit is
`experiments/provider_environment_preflight_audit_20261016.json`, SHA-256
`bf0d118398a8191fdd461c1913a4d321650449da61e8c87b302bc238d3ad82a4`.
It confirms:

- base URL `https://antchat.alipay.com/v1`;
- model `DeepSeek-V4-Flash`;
- maximum concurrency 5;
- exact CA SHA-256
  `9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f`;
- only certifi as a third-party transport dependency; and
- zero credential reads, profile reads, request/response-body reads, API calls,
  model calls, solver calls, native-evaluator calls, or VM calls.

This is a public transport and environment preflight. It does not serialize or
replay private experiment envelopes, establish account authorization, contact
the provider, or guarantee future provider behavior. Offline result
reconstruction remains the public reproducibility route; a live replay requires
the separately held private protocol material, account, credential, and author
authorization.
