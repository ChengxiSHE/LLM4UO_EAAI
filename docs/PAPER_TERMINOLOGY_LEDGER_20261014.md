# Paper terminology ledger

Status: canonical manuscript vocabulary, 2026-10-14.  Use these forms across
the title, abstract, main text, figures and Supplementary Information.  Do not
introduce synonyms merely for stylistic variety.

| Canonical term | First-use definition | Variants to avoid or restrict | Decision |
| --- | --- | --- | --- |
| Benchmark-Grounded Proof-Carrying Knowledge Compilation | A methodology that constructs typed optimization knowledge programs from benchmark development failures, admits them through fixed verification and compilation, routes them from public input, and promotes versions through a frozen endpoint | VERA-Opt, ARK, self-improving Codex, automatic harness optimization, generic skill-evolution priority | Primary paper-facing method name; acronym should be omitted unless the final title requires one |
| Benchmark-Grounded Proof-Carrying Skill Evolution | Former paper-facing name preserved only in frozen protocols, historical reviews and immutable evidence narratives | current method name | Treat as a historical alias; do not rewrite frozen artifacts or use it in new paper-facing prose |
| skill | A tuple containing an applicability guard, typed evidence extractor, transformation, verifier, resource checker and provenance | prompt, hint, memory | Use `skill` only for the typed executable artifact |
| skill library | A content-addressed set of skills plus a public-only router, immutable verifier, frozen endpoint and lineage ledger | knowledge base, memory bank | `knowledge base` may appear once for accessibility, then use `skill library` |
| skill evolution | A frozen candidate-generation, verification and promotion transition between library versions | unrestricted RSI, autonomous self-improvement | Use only when a version transition follows the declared protocol |
| proof-carrying compilation | Compilation of a typed transformation together with checkable semantic and resource obligations | formal proof of language understanding | State the conditional boundary at first use |
| public-only router | A rule that sees no evaluator answer and returns exactly one pinned skill or abstains | oracle router, family-label selector | Canonical routing term |
| strong static control | A frozen non-evolving policy using the same public interface, compiler and solver where applicable | Base, weak baseline | Primary comparator for evolution claims |
| Base | The experiment-specific frozen generator or backend output before selective skill replacement | strong static control | Define separately for each experiment; never merge the two terms |
| promotion | Outcome-hidden grouped evaluation used to accept or reject a frozen candidate version | validation, confirmation | Reserve for the predeclared library-transition gate |
| confirmation | One-shot evaluation after method, comparator, router and endpoint are frozen, with no subsequent adaptation | test replay, promotion | Reserve for the final untouched stage |
| benchmark formulation accuracy | Agreement with the benchmark's fixed final status/objective or accepted-output endpoint on the full assigned denominator | semantic equivalence, compile rate | Primary effectiveness endpoint; define benchmark-specific endpoint |
| source-corrected OR-Debug endpoint | Repair equivalence after correcting the released Type-B LP variable-domain inconsistency, plus executable optimality and collateral-change checks | corrected accuracy without explanation | Primary OR-Debug endpoint; always report the released endpoint separately |
| abstention | Explicit refusal caused by unsupported or ambiguous public evidence, counted as incorrect in the full denominator | unavailable, infrastructure failure | Keep distinct from transport or solver failure |
| correction | Static/previous policy wrong and evolved policy correct on the same assigned record | gain | Report with regressions and denominator |
| regression | Static/previous policy correct and evolved policy wrong on the same assigned record | error | Report even when zero; zero observed is not a universal guarantee |
| official-code reproduction | Local execution from a pinned author artifact with every adaptation disclosed | paper result, native reproduction | Do not use when only a paper-based reimplementation exists |
| safe-adapter result | Result obtained through the bounded interpreter or restricted execution bridge | native method accuracy | Report unsupported-output coverage explicitly |
| automatic proposer | A bounded procedure that proposes a skill within the same frozen grammar and evidence contract | autonomous evolution | Tested once with a negative verifier result; not an established contribution |

## Notation lock

Use `L_t=(K_t,rho_t,V,E,ledger_t)` for library state.  Use `K_t` for the
content-addressed skill set, `rho_t` for the public-only router, `V` for the
immutable verifier, `E` for the frozen benchmark endpoint, and `ledger_t` for
accepted and rejected lineage.  Use `A(x)` for router acceptance, `B(x)` for
the frozen comparator output and `K(x)` for a candidate skill output.  Do not
reuse `E` for evidence or `V` for a model version in the same manuscript.

## Claim-language lock

- Use **multi-source replication of the methodology** for the joint TSP and
  OR-Debug evidence.
- Do not write **cross-source transfer** unless one unchanged skill is applied
  to a distinct source.
- Use **authored skill** for the current TSP and OR-Debug rules.
- Do not write **automatically synthesized skill** until a matched proposer
  treatment yields a verifier-valid candidate and passes independent promotion.
- Use **bounded verifier-mediated evolution** when relating the work to RSI.
- Do not write **recursive self-improvement** without the qualifier `bounded`
  and a sentence stating that the verifier, endpoint and resource policy are
  not self-modified.
