# Credential-free clean-clone Layer A audit

Status: **passed with an explicit external-submodule acquisition boundary**, 2026-10-15.

The evidence-integrity layer was reconstructed from commit
`1a5033b8de26174dd65ac3444cf3bcd88202032e` on branch
`codex/typed-count-cegis-revision-20261014`. The main repository was copied
with `git clone --no-local`. The declared GitHub solver submodule could not be
acquired remotely: one recursive attempt failed with an HTTP/2 framing error
and its retry timed out after 75 seconds; a separate HTTP/1.1 `ls-remote` probe
also timed out after 25 seconds.

The bounded offline fallback therefore copied the already initialized local
solver checkout at the exact pinned commit
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` into the isolated clone and
registered it as the submodule. This local checkout is a shallow partial clone,
so the audit explicitly records both `remote_acquisition_verified=false` and
`complete_object_graph_verified=false`. The fallback establishes neither
remote availability nor a complete solver release artifact.

Inside the isolated clone, commands inherited no parent environment values.
The only available variables were `GIT_CONFIG_NOSYSTEM`,
`GIT_TERMINAL_PROMPT`, `HOME`, `LANG`, `LC_ALL`, `PATH`,
`PYTHONDONTWRITEBYTECODE` and `PYTHONHASHSEED`; no credential or provider
variable was present. Python 3.10.1 then completed:

- 51 credential-free unit tests covering content-addressed manifests, current
  library reconstruction, release-evidence reconstruction, clean-clone policy,
  verified skill routing and mixed identity;
- byte-identical current skill/library manifest reconstruction;
- 2,985/2,985 body-free direct-versus-mixed identity reconstruction; and
- the existing 69-path, 408-assertion, 15-boundary paper evidence integrity
  check and 118-reference/107-unique-path goal evidence check.

The clone was clean before and after all checks. No API, model, solver, native
evaluator or VM was called. No request or response body, evaluator-only answer,
credential or parent environment value was read. The machine audit SHA-256 is
`bcc97f407f2e72c9a7338dc4f8c6ead02cd026921513be47fa866535a8e43d91`.

This closes the credential-free Layer A code-and-evidence reconstruction for
the audited commit under a local pinned partial-submodule snapshot. It does not
close the offline dependency layer, solver/native replay, provider replay,
figure regeneration, third-party remote acquisition, license and attribution,
historical publisher replacement, or history-safe public release. A later
network-available run must repeat the same runner without the local-submodule
option before claiming recursive remote acquisition.
