# Data and Code Availability Audit — 2026-10-15

## Status

The project is **not yet submission-ready as a public reproducibility package**.
The scientific evidence is locally bound by hashes, but release engineering and
third-party rights are not closed. In the current paper manifest, only 7 of 46
bound files are Git tracked; 39 remain untracked. The manifest itself and both
goal-audit companions are also untracked control files outside the self-bound
count. The repository root has no first-party license. Two tracked files remain below `results/private/`; one contains
OPT-Engine task text. A third tracked file,
`experiments/mixed_skill_confirmation_bundle_20261014.json`, embeds 140 TSP
`public_text` records from the same source. That upstream repository has no
explicit license file in the audited revision.

This audit concerns availability and redistribution. It does not alter any
reported result, reopen a closed experiment, or establish rights that the
upstream authors have not granted.

## Asset inventory and release route

| Asset | Pinned source | Current route | Release condition |
|---|---|---|---|
| First-party code, skills, manifests and paper documents | This repository, HEAD `22927e96fcced15de3cc5af5cd220febdb8942cc` | Curated public repository release | Author must select a root license and prepare an explicit allowlist commit for 39 untracked bound paths plus the self-describing release-control files |
| Headline result summaries and closures | Hash-bound local JSON artifacts | Publish non-secret terminal summaries and verification records | Add the currently untracked files and complete content-level redaction review |
| TSP / OPT-Engine | `Cardinal-Operations/OPTEngine` at `d84a4b49187071debf16f50ba03a193776213edd` | Users retrieve the pinned upstream snapshot; this project publishes hashes, split metadata, derived aggregates and reconstruction instructions | Do not redistribute raw task text until explicit upstream terms are verified |
| OR-Debug / solver-in-the-loop | Git submodule at `c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` | Pinned submodule with attribution | Preserve the upstream CC BY 4.0 license and initialize recursively |
| DCP-Bench-Open | `DCP-Bench/DCP-Bench-Open` at `3f7e121301e0ea4565e20d8ee0660e799686c194` | Users retrieve the pinned upstream revision | Repository is Apache-2.0; inherited sources still need per-source rights review |
| BIND / text2opt-bench | `SprocketLab/text2opt-bench` at `1dac06be656c41d827ef20987cf8af0b48d382a2` | Pinned upstream retrieval plus local adapter metadata and aggregate results | Review upstream terms before redistributing source assets |
| CoE | `xzymustbexzy/Chain-of-Experts` at paper commit `9d96bcc2f067177eb0e122b1aae8227748dc6830` and current commit `afb89bf602690ea621f13a23c42722f20f653a43` | Pinned retrieval instructions, safe-adapter description and aggregate results | Do not vendor the upstream code unless an explicit license is verified |
| OptiTrust | arXiv `2508.03117v1` | Cite source and disclose artifact unavailability | No verified runnable official artifact was found; do not substitute a published score |
| API accounting | Local metadata-only ledgers | Publish only reviewed aggregate accounting and terminal status | Exclude credentials, request and response bodies, and evaluator-only answers |

The tracked-data manifests are provenance records rather than a blanket grant
to redistribute every upstream dataset. The ignored `data/raw/`, prepared-data
and private-result trees should remain outside the release unless each file is
explicitly reviewed and allowlisted.

## Environment and reconstruction constraints

The recorded offline environment uses Python 3.11.16 with NumPy 2.4.4, SciPy
1.17.1, jsonschema 4.26.0 and scikit-learn 1.9.0. The machine's default Python
is 3.10.1, so reproduction instructions must select the verified environment
explicitly. Gurobi 13.0.1 was used for solver-backed evaluations; it is
commercial software and each reproducer must obtain a valid installation and
license independently.

The tracked `requirements-offline.txt` pins NumPy, SciPy, jsonschema and
scikit-learn for Python 3.11 offline evidence verification. It does not yet lock
the provider transport, Gurobi/native-evaluator environment or all upstream
reconstruction dependencies. The OR-Debug dependency is a pinned Git
submodule. A clean checkout must run:

```bash
git submodule update --init --recursive
```

The current superproject reports the submodule as not initialized, so a clean
clone has not yet been used to verify the full release procedure.

## Blocking issues before submission

1. Select a first-party license and add it at the repository root. This choice
   belongs to the authors; the audit does not infer one.
2. Prepare a narrow allowlisted release commit for the 39 manifest-bound files
   currently untracked, plus the paper manifest and goal-audit control files.
3. Remove the two tracked private TSP paths and the public-text-bearing mixed
   bundle from the public release, or replace them with rights-safe identities,
   hashes, routing metadata, split metadata, aggregate projections and
   deterministic reconstruction from the pinned upstream revision.
4. Freeze a disclosure policy for prompts, model outputs, compile diagnostics
   and API ledgers, then inspect the allowlist contents rather than relying only
   on filename and generic-secret scans.
5. Extend the tracked offline requirements with the complete provider,
   solver/native-evaluator environment and one clean-checkout procedure that
   reconstructs each licensed upstream source at its pinned revision and
   rebuilds every headline table.
6. Verify that procedure in a clean clone without private data, caches or local
   credentials.
7. Mint an archival DOI or immutable software citation only after the curated
   release exists; no DOI is currently claimed.

## Manuscript-ready drafts

The following text is a **draft template**. Bracketed items and future-tense
commitments must be replaced only after the release is completed.

### Data Availability

The experiments use publicly obtainable benchmark sources at pinned revisions.
OPT-Engine data will be retrieved from the upstream repository at commit
`d84a4b49187071debf16f50ba03a193776213edd`; because explicit redistribution
terms were not verified, the release will provide file hashes, split metadata,
derived aggregate results and reconstruction scripts rather than the raw task
text. OR-Debug data are pinned through the solver-in-the-loop submodule at
commit `c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010` under its upstream CC BY 4.0
terms. DCP-Bench-Open is pinned at commit
`3f7e121301e0ea4565e20d8ee0660e799686c194`; inherited sources remain subject
to their own provenance and rights conditions. BIND and CoE assets will be
retrieved from their pinned upstream revisions rather than silently relicensed
by this project. Non-secret split manifests, hashes, aggregate outputs and
terminal evaluation records will be released at [ARCHIVAL REPOSITORY AND DOI
TO BE ADDED]. Credentials, request and response bodies, evaluator-only answers
and third-party data lacking verified redistribution rights will not be
released.

### Code Availability

The implementation, typed skill definitions, public-only router, verifier and
evaluation scripts will be released at [ARCHIVAL REPOSITORY AND DOI TO BE
ADDED] under [AUTHOR-SELECTED FIRST-PARTY LICENSE]. The release will identify
the exact software revision, initialize the pinned solver-in-the-loop
submodule, provide a Python 3.11.16 environment specification, and document
which evaluations require a separately licensed Gurobi 13.0.1 installation.
It will also include machine-readable evidence manifests that bind headline
claims to immutable file hashes and field-level assertions. Third-party code
without a verified redistribution license will be referenced by repository and
commit rather than vendored.

## 作者提交前核对项

- [ ] 选择并确认仓库根许可证；不要由工具代替作者作法律选择。
- [ ] 用明确 allowlist 提交 39 个尚未追踪的论文证据文件及三个清单控制文件。
- [ ] 清理两个已追踪的 `results/private/` TSP 路径以及内嵌140条TSP题面的mixed bundle，并确认 Git 历史处理方案。
- [ ] 对准备发布的每个文件执行正文级隐私、密钥、题面许可和答案泄露审计。
- [ ] 从干净克隆初始化子模块并完整重建论文核心表格。
- [ ] 在真实归档完成后填写 DOI、软件版本和引用信息。
- [ ] 将最终 Data/Code Availability 文本中的所有方括号占位符替换为真实信息。

The current machine-readable companion is
`experiments/release_readiness_delta_v2_20261015.json`; the original
`experiments/release_readiness_20261015.json` remains as the historical v1
snapshot.
