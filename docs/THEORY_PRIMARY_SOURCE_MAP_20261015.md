# Primary-source map for the theoretical framework

Status: verified paper-planning artifact, 2026-10-15. This document maps each
theoretical ingredient of **Benchmark-Grounded Proof-Carrying Knowledge Compilation**
to a primary source, the exact role it may play in the paper, and the boundary
that prevents inherited theory from being presented as a new theorem. Citation
keys refer to [`manuscript/references.bib`](../manuscript/references.bib).

## Scope and source policy

This map covers the method's theoretical backbone. It does not certify the
project's empirical numbers; those remain bound by
[`experiments/paper_evidence_manifest_20261015.json`](../experiments/paper_evidence_manifest_20261015.json).
Each source below is an author, venue, journal, or publisher record for the
original contribution. Secondary surveys may later be added for exposition but
must not replace these records when establishing priority.

## Claim-to-source map

| Project ingredient | Primary source | Legitimate use in this paper | Required boundary |
| --- | --- | --- | --- |
| Finite typed candidate grammar | Alur et al., *Syntax-Guided Synthesis* (`alur2013sygus`) | Motivate a grammar that restricts candidate skill programs while a semantic specification defines acceptance | The project's grammar, oracle and optimization-modeling contracts are authored artifacts; the project does not introduce SyGuS itself |
| Counterexample-guided candidate elimination | Solar-Lezama et al., *Sketching Concurrent Data Structures* (`solarlezama2008sketching`) | Ground the propose-check-counterexample loop and monotone elimination of inconsistent candidates | Finite termination and enumerated-domain soundness apply only to the declared grammar, verifier and domain |
| Untrusted producer with a trusted admission checker | Necula, *Proof-Carrying Code* (`necula1997proofcarrying`) | Motivate accepting model- or human-proposed skill artifacts only when their declared obligations are mechanically checkable | The current certificates do not prove natural-language understanding or universal formulation equivalence |
| Per-output validation instead of trusting a transformer globally | Pnueli, Siegel and Singerman, *Translation Validation* (`pnueli1998translation`) | Motivate checking each compiled formulation and its projection rather than claiming the compiler is correct for every possible source | The checks establish only the encoded semantic and resource obligations; omitted obligations remain outside the guarantee |
| Abstention and risk-coverage reporting | El-Yaniv and Wiener, *On the Foundations of Noise-Free Selective Classification* (`elyaniv2010selective`) | Ground the separation among coverage, selective risk and full-denominator endpoint accuracy | The current router is deterministic on frozen public envelopes; it is not a calibrated learned selective classifier under distribution shift |
| Separating-witness selection over a finite version space | Nowak, *The Geometry of Generalized Binary Search* (`nowak2011gbs`) | Motivate choosing public counterexamples that split the remaining candidate skills rather than returning an unordered failure list | Logarithmic query bounds require the paper's missing balance or geometric assumptions; no such bound is currently claimed for the LLM proposer |
| Compact skill selection | Blumer et al., *Occam's Razor* (`blumer1987occam`) | Support the principle that a compact consistent hypothesis class can admit finite-sample learning guarantees | The present description-length inequality requires a frozen label-independent prefix code and valid independent evaluation units; authored same-development grammars do not satisfy that premise |
| High-confidence improvement relative to a baseline | Thomas, Theocharous and Ghavamzadeh, *High Confidence Policy Improvement* (`thomas2015hcpi`) | Provide related theoretical context for promoting a new library version only when a lower confidence bound clears the frozen baseline | The project's alpha allocation is a separate grouped benchmark-testing construction; it does not inherit an MDP or off-policy-evaluation guarantee from HCPI |

## What is inherited and what is project-specific

The individual ingredients above are established theory. The paper must not
claim novelty for finite CEGIS, proof-carrying code, translation validation,
selective classification, Occam learning, generalized binary search, or
high-confidence policy improvement.

The project-specific contribution is their executable composition for
LLM-to-optimization modeling:

1. benchmark failures are converted into typed modeling obligations rather
   than unconstrained prose memories;
2. a candidate skill combines a public guard, typed evidence extraction,
   formulation transformation, semantic checks, exact resource checks and
   provenance;
3. counterexamples and rejected candidates remain in an immutable version
   lineage;
4. a public-only router either selects one pinned skill or returns the frozen
   previous-library output;
5. full-denominator benchmark accuracy, corrections and regressions decide
   promotion; and
6. the verifier, evaluator and promotion policy remain outside the state an
   untrusted proposer may edit.

This combination supports the term **bounded verifier-mediated skill
evolution**. It does not support unrestricted recursive self-improvement.

## Concurrent skill-library neighborhood

The general skill-library framing also has close 2026 precedents. SkillOpt
(`yang2026skillopt`) optimizes a textual skill under held-out validation;
SkillOps (`pu2026skillops`) uses typed skill contracts for library maintenance;
SkillSpec (`chen2026skillspec`) combines consensus-gated updates with
representation specialization; SkillForge (`yang2026skillforge`) and Skill-V
(`ma2026skillv`) explicitly study verified skill evolution; HASP
(`liu2026hasp`) turns skills into guarded executable programs; and SkillsBench
(`li2026skillsbench`) formalizes paired skill/no-skill evaluation with
deterministic verifiers. These are priority and positioning sources rather
than sources for the propositions proved in this supplement.

Accordingly, the paper must not claim priority for typed skill contracts,
validation-gated skill updates, versioned or falsifiable skills, applicability
filtering, executable skill programs, or paired evaluation in general. The
project-specific object is narrower: an optimization-modeling skill carries
mechanically checked formulation semantics and exact resource obligations,
uses a frozen solver-facing formulation endpoint, preserves the previous
library exactly outside unique public coverage, and is promoted on
lineage-separated paired benchmark evidence.

## Theory-to-current-evidence boundary

| Theoretical statement | Current project evidence | Evidence status |
| --- | --- | --- |
| A finite grammar can be exhausted and a minimum repair identified | The count certificate checks all 64 hypotheses, rejects all six distance-one neighbors and identifies one unique distance-two repair | Established within the frozen grammar and verifier |
| A proof-carrying skill can improve the benchmark endpoint | TSP improves `54/140` to `100/140`; OR-Debug improves `828/2845` to `2752/2845`, both with zero observed paired regressions | Confirmed on two frozen benchmark-source studies; not a universal correctness theorem |
| Selective composition can preserve direct behavior | The mixed public router reproduces all 2,985 frozen direct-family outputs exactly | Established for the frozen known envelopes; no paraphrase or shift claim |
| Interaction-aware witnesses improve automatic skill construction | The exact repair shows a two-field semantic-resource interaction, but the first bounded model proposal fails the resource gate | Hypothesis only; the matched flat-versus-interaction-aware experiment has not run |
| Compact skills enjoy a project-level generalization guarantee | A conditional prefix-code bound is stated in the theory note | Not established for the current authored development grammars |
| Repeated library updates control erroneous promotion | OR-Debug uses one frozen promotion gate followed by confirmation | One realized transition; repeated-generation control still depends on fresh valid groups and prespecified error allocation |

## Paper language controls

Use these formulations:

- "Our construction instantiates a finite SyGuS/CEGIS problem."
- "The skill is proof-carrying with respect to declared semantic and resource
  obligations."
- "The router implements deterministic selective adoption with an unchanged
  fallback."
- "Promotion is benchmark-tested under a prespecified grouped error budget."
- "Separating-witness feedback is motivated by version-space reduction and is
  evaluated as an empirical treatment."

Do not use these formulations:

- "We introduce CEGIS, proof-carrying code or selective prediction."
- "Verifier acceptance proves the natural-language formulation correct."
- "Zero observed regressions proves distribution-free non-regression."
- "The current proposer automatically discovered the useful skill."
- "The library performs unrestricted recursive self-improvement."
- "Generalized binary search guarantees logarithmic LLM requests" without
  first establishing its balance or geometric assumptions.

## Citation verification record

The theoretical-source entries and seven concurrent skill-library entries in
`manuscript/references.bib` were checked against primary author, venue, journal
or arXiv records on 2026-10-15. DOI-bearing entries use
the DOI displayed by those records. The JMLR and PMLR entries use their canonical
article pages. This file records bibliographic and claim-scope verification; it
does not assert that every later manuscript sentence is correctly cited. A final
claim-level citation audit remains required after the manuscript text is frozen.
