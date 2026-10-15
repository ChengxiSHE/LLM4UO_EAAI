# Provider transport environment preflight

Date: 2026-10-15  
Status: **local transport preflight passed; real replay remains external**

## What was verified

The frozen AntChat transport for the current experiments uses Python's standard
library for HTTP, TLS, multiprocessing and JSON. Its only third-party runtime
dependency is `certifi==2026.7.22`. The installed CA bundle contains 240,216
bytes and matches the source-bound SHA-256
`9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f`.

The credential-free preflight verified all of the following:

- the endpoint is `https://antchat.alipay.com/v1`;
- the model is `DeepSeek-V4-Flash`;
- provider, request-contract and transport modules agree on endpoint and model;
- the TLS context requires hostname and certificate verification;
- the transport imports neither the OpenAI SDK nor `requests`;
- the repository requires no provider package beyond the pinned CA bundle;
- the recorded experiment concurrency remains 5.

Run the local preflight with:

```text
python -m pip install -r requirements-provider.txt
python scripts/verify_provider_environment.py --check
```

The machine-readable audit is
`experiments/provider_environment_preflight_audit_20261015.json` with SHA-256
`7903dd96df3d8b709b7fabbea108b2299184e93124d6baac1ee9191c65ccb558`.

## Boundary

This check deliberately does not inspect the private profile's metadata or
contents, load an API key, connect to AntChat, resend a request, inspect a
request/response body, or claim that a provider account is authorized. It
makes zero model, API, solver, native-evaluator or VM calls.

Accordingly, this closes the *local transport dependency and TLS preflight*
part of the provider layer. Real trajectory replay still depends on an
externally provisioned credential, account authorization, provider service and
network. Public, credential-free reproduction uses the frozen body-free
projections and ledgers; it does not silently resend the study.
