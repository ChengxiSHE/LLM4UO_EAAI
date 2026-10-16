# Manuscript outline — Benchmark-Grounded Proof-Carrying Knowledge Compilation

Updated 2026-10-14. This outline is synchronized with the current theory,
terminal TSP and OR-Debug confirmations, the frozen mixed-router replay, the
fixed common-40 external comparison, and the negative first automatic
proposer. It supersedes the earlier V9/VERA-Opt-centered outline.

## Paper identity

**Working title:** Benchmark-Grounded Proof-Carrying Knowledge Compilation for
Reliable Optimization Modeling

**Central claim:** optimization-modeling knowledge can be represented as
versioned typed skill programs rather than prompt text. Benchmark failures
motivate finite candidate languages; a fixed verifier and compiler enforce
declared semantic and resource obligations; a public-only router deploys one
unambiguous skill or abstains; and a frozen endpoint decides promotion. This
methodology improves strong static controls on prospective TSP and OR-Debug
confirmation splits, while its guarantees remain conditional on the typed
contract, verifier and evaluator.

The paper must not use VERA-Opt, RSI, self-improving Codex or automatic harness
optimization as the current method name. V9 and typed BinPacking are historical
anchors for selective trusted compilation. The first bounded automatic
proposer is a negative result.

## Research questions

1. **RQ1 — endpoint value:** can a proof-carrying skill improve
   full-denominator benchmark formulation accuracy over a strong frozen static
   control?
2. **RQ2 — methodological replication:** can the same acquisition,
   verification, routing and promotion methodology work on a second benchmark
   source and a different optimization-modeling task?
3. **RQ3 — composition:** can multiple confirmed skills be composed behind one
   public-only fail-closed router without changing their direct behavior?
4. **RQ4 — knowledge acquisition:** does interaction-aware
   separating-witness feedback improve verifier-valid skill discovery over
   flat feedback under matched information and cost?

RQ1–RQ3 have terminal evidence. RQ4 remains open: the initial proposer failed
the resource gate, and the matched causal comparison has not run.

## Abstract evidence chain

Write the abstract last from this six-step chain:

1. Language models can emit executable optimization models whose omitted or
   misbound relations survive syntax checks and solver execution.
2. Existing prompt, repair and agent workflows generally treat reusable
   knowledge as text and do not separate proposal, verification, routing and
   promotion.
3. We study Benchmark-Grounded Proof-Carrying Knowledge Compilation, representing
   a skill as a guard, typed evidence extractor, transformation, semantic
   verifier, resource checker and provenance record.
4. On frozen TSP confirmation, a strong static controller scores 54/140 and the
   typed constraint skill 100/140, with 46 corrections and zero regressions.
   On OR-Debug confirmation, a generic fresh-IIS static policy scores 828/2845
   and the typed repair library 2752/2845, with 1,924 corrections and zero
   regressions.
5. A mixed public-only router reproduces all 2,985 frozen direct-family outputs
   exactly. Local BIND and CoE reproductions establish comparator and execution
   boundaries rather than an unconditional leaderboard.
6. A bounded automatic proposer passes 20,977 semantic assignments but fails
   an exact resource obligation; exhaustive verification proves a unique
   minimum two-field repair. This exposes the remaining acquisition problem
   rather than claiming autonomous skill learning.

Do not describe finite-domain soundness as universal formulation correctness,
the mixed replay as fresh accuracy, two separately authored skills as one skill
transferring across sources, or the negative proposer as automatic recovery.

## 1. Introduction

### 1.1 Problem

- A solver can optimize a malformed model, so parseability, solvability and
  even objective agreement do not prove formulation fidelity.
- Free-form guidance is difficult to version, route, verify and retire.
- Iterative self-review can repeat the same semantic omission.
- Benchmark gains must retain abstentions, unsupported outputs,
  infrastructure failures and regressions in a declared denominator.

### 1.2 Proposed view

Treat reusable modeling knowledge as a small program with an explicit contract:

    k = (g, e, t, v, r, p)
    L_t = (K_t, rho_t, V, E, ledger_t).

The proposer is untrusted. The verifier and benchmark endpoint are outside the
state it may edit.

### 1.3 Contributions

1. An executable methodology combining finite counterexample-guided
   construction, proof-carrying compilation, selective routing and
   risk-controlled library promotion.
2. Bounded theoretical results for finite termination, enumerated-domain
   extensional correctness, declared resource compliance, accepted-path
   correctness and anytime promotion error under stated assumptions.
3. Prospective TSP confirmation against a strong static controller.
4. Independent methodological replication on OR-Debug-Bench with grouped
   promotion and confirmation.
5. Exact retrospective composition of the two confirmed skills behind a single
   public-only router.
6. Audited local BIND and CoE reproductions, an explicit official OptiTrust
   artifact-availability boundary, an infrastructure-clean negative
   OptiTrust-style indexed method preflight, and a falsifiable negative
   automatic-construction trace with an exact minimum-repair certificate.

## 2. Related work

Organize the section by methodological questions rather than system names.

### 2.1 Language-to-optimization modeling

Discuss Text2Opt/BIND, CoE, OptiTrust and related formulation agents in terms of
their public input, feedback, output contract, execution environment and
endpoint. Published scores are literature context, not local empirical rows.

### 2.2 Program synthesis and counterexample-guided learning

Relate the finite typed grammar and retained counterexamples to SyGuS and CEGIS.
The grammar and oracle are authored components; finite enumeration is not a new
general synthesis algorithm.

### 2.3 Proof-carrying and verified compilation

Position semantic obligations and exact resource certificates relative to
proof-carrying code, translation validation and neuro-symbolic compilation.
The verifier establishes only its declared contract.

### 2.4 Selective prediction and abstention

Connect public-only guards, ambiguity rejection, risk-coverage behavior and
unchanged fallback to selective prediction. Fallback identity is structural;
population non-regression remains statistical.

### 2.5 Agent and skill evolution

Compare versioned skills, automated agent design and bounded recursive
improvement. The current method updates external skill artifacts under an
immutable verifier and endpoint; it does not modify model weights or establish
unrestricted RSI.

## 3. Problem setting and evaluation contracts

### 3.1 Benchmark-specific endpoints

- TSP: frozen public graph envelope, trusted exact backend and prescribed
  status, tour and objective endpoint.
- OR-Debug: corrupted LP/MIP model, typed repair operation and independent
  corrected-model endpoint.
- External fixed-40: RCPSP and VRPTW identities under each method's disclosed
  interface and safe execution adapter.

Do not imply that these endpoints are numerically interchangeable.

### 3.2 Accuracy and paired effects

For acceptance indicator A, previous output B and skill output K:

    Acc(new) - Acc(old)
      = P(A, B wrong, K right) - P(A, B right, K wrong).

Report corrections, regressions, abstentions, failures, coverage and
full-denominator accuracy. Compilation rate and verifier acceptance are
mechanism metrics, not substitutes for accuracy.

### 3.3 Custody and information boundary

- Skills and controls freeze before confirmation outcomes are opened.
- Routers use public inputs only.
- Evaluator-only references cannot select, repair or route candidates.
- Unsupported and unavailable outcomes remain in the declared denominator.
- Related templates are grouped for promotion and inference.

## 4. Method

### 4.1 Typed skill contract

Define guard g, evidence extractor e, transformation t, semantic verifier v,
resource checker r and provenance p. State which components are authored,
model-proposed or mechanically checked in each instantiation.

### 4.2 Finite counterexample-guided construction

For benchmark family b, freeze candidate language H_b, verification domain D_b
and contract oracle O_b. Retain the first hashed counterexample for each failed
candidate and eliminate it. Candidate programs must also pass the unchanged
compiler and resource guards.

### 4.3 Complexity-aware knowledge selection

Select compact candidates using paired corrections, regressions, serialized
description length and execution cost, with semantic and resource violations
as hard constraints. Present the prefix-code Occam bound only under independent
evaluation units and a label-independent frozen candidate family. Do not apply
it retrospectively to authored development grammars.

### 4.4 Proof-carrying compilation

Separate source-contract applicability, complete typed evidence extraction,
solution and objective preservation under projection, exact resource counts,
and exact solving and output projection. An accepted-path correctness statement
is conditional on every premise.

### 4.5 Selective public-only routing

Exactly one matching guard selects a pinned skill. Zero or multiple matches
abstain to the frozen previous-library output. Learned routing is outside the
current claim.

### 4.6 Risk-controlled promotion and versioning

Freeze candidate and router before promotion. Allocate generation-level error
budgets, evaluate on lineage-separated groups, record corrections and
regressions, and archive both accepted and rejected transitions. Each version
records parent, skill, verifier, endpoint, plan and rollback hashes.

## 5. Theory and guarantees

### 5.1 Finite termination

If H_b is finite and every rejection eliminates its candidate, construction
terminates after at most |H_b| decisions.

### 5.2 Enumerated-domain soundness

If every x in D_b is checked and acceptance requires h(x)=O_b(x), the accepted
program is extensionally correct on D_b. This says nothing about inputs outside
D_b, oracle errors or language faithfulness.

### 5.3 Exact minimum repair

Exhaustive evaluation under a frozen Hamming metric identifies the minimum
passing repair within the declared grammar. It does not prove grammar
completeness or model discovery.

### 5.4 Conditional compilation and routing properties

State conditional resource safety, accepted-path correctness, fallback
identity and the conservative-extension corollary. Keep empirical zero
regressions separate from a distribution-free dominance theorem.

### 5.5 Anytime promotion control

With fresh valid evaluation groups and prespecified sum(alpha_t) <= alpha, a
union bound controls the probability that any promoted version violates its
stated promotion condition. The proposition does not protect against an
incorrect evaluator or dependent pseudo-replicates.

## 6. Experimental design

### 6.1 TSP first-source confirmation

- Freeze the typed constraint skill and strong canonical static controller.
- Use the size-13–19 confirmation split.
- Count all 140 identities and all skill abstentions.
- Report results by size as well as the paired aggregate.

### 6.2 OR-Debug second-source replication

- Construct the repair library from development errors.
- Compare against a generic fresh-IIS static repair policy.
- Use a 37-group promotion gate and one-shot 100-group confirmation.
- Retain ambiguous cases as abstentions in the full denominator.

### 6.3 Mixed-router composition

- Interleave the frozen 140 TSP and 2,845 OR-Debug public envelopes.
- Require one expected route, no ambiguity, no execution failure and exact
  equality with the pinned direct-family compact output.
- Treat inherited accuracy as descriptive, not a new score.

### 6.4 External fixed-40 panel

- Use the same 40 RCPSP/VRPTW identities where available.
- Pin official repositories and commits.
- Separate author-exact, tolerance and unsupported-adapter outcomes.
- Separate BIND answer-blind first round from answer-bearing final repair.
- Keep OptiTrust artifact-unavailable until a verified official package exists;
  any paper-based recreation must be labeled separately. Preserve the indexed
  adapter as a negative method preflight: its transport passes, its method gate
  fails, and it has no accuracy row.

### 6.5 Construction mechanism study

Completed diagnostic:

- one bounded AntChat proposer request;
- frozen 64-candidate typed count grammar;
- 20,977 semantic assignments plus exact compiler resource obligations;
- answer-free exhaustive minimum-repair certificate.

Remaining matched experiment:

- same eight stratified source candidates in both arms;
- flat and interaction-aware feedback contain identical atomic facts;
- same model, grammar, schema, output ceiling, budget and verifier;
- primary outcome: verifier pass;
- secondary outcomes: minimum-repair hit, valid response, token cost and
  regression;
- prespecified expansion gate: at least two net paired corrections and zero
  regressions.

The remaining experiment must not expose reference answers, author-selected
winner identities or evaluator-only material.

## 7. Results

### 7.1 TSP skill improves prospective endpoint accuracy

Static 54/140 versus skill 100/140; 46 corrections, zero regressions, +32.86
percentage points. Gains are positive at every size from 13 to 19. All 40 skill
abstentions remain incorrect in the denominator.

### 7.2 OR-Debug replicates the methodology on a second source

Static 828/2845 (29.10%) versus skill 2752/2845 (96.73%); 1,924 corrections,
zero regressions, +67.63 points. Of 100 held-out structural groups, 65 improve,
35 tie and none decline; prespecified group sign-test p=2.71e-20. All 93
abstentions remain incorrect.

### 7.3 Public-only composition preserves direct behavior

All 2,985 records route uniquely to the expected family. Every mixed output
equals its direct-family output; there are zero route mismatches, failures,
missing outputs, duplicates or unexpected records.

### 7.4 External reproductions establish comparison boundaries

- BIND: 31/40 answer-blind first round; 40/40 after official answer-bearing
  feedback.
- CoE paper/current snapshots: author-exact 3/40 and 1/40 under the safe
  adapter; 25 and 29 completed outputs unsupported by that adapter.
- OptiTrust: the inspected official arXiv v1 source contains no runnable
  implementation, complete prompts, training data, checkpoint or inference
  script.
- OptiTrust-style indexed adapter: the v4 transport gate passes, but two frozen
  two-family method gates produce zero optimal review views and zero consensus
  cells; common-38 is not dispatched and no accuracy estimate is reported.

Do not rank the confirmed TSP/OR-Debug results against these fixed-40 rows.

### 7.5 Automatic proposal fails; exact repair reveals an interaction

The proposer returns a valid grammar member that passes every semantic
assignment but fails the resource gate. All six distance-one repairs fail;
bound-only repair creates a zero-tail semantic counterexample, and
zero-tail-only repair retains the resource failure. Their joint change is the
unique passing distance-two repair. Attribute the repair to exhaustive
verification, not the model.

### 7.6 Historical anchors and negative studies

Use V9 200/400 -> 259/400 and typed BinPacking 37/160 -> 158/160 as motivation
for trusted compilation and selective adoption. Condense DCP guidance,
order-interface, format and recovery studies into a failure analysis:
compilation, local feedback and candidate recovery did not reliably predict
frozen endpoint promotion. Keep complete trajectories in the supplement.

## 8. Discussion

### 8.1 What the evidence supports

- benchmark-grounded, typed skill engineering can improve final endpoint
  accuracy over strong static controls;
- complete authored systems improve endpoints across a construction task and a
  repair task, without isolating architecture from knowledge content;
- frozen family skills can compose behind an exact public-only interface; and
- rejected candidates and verifier counterexamples yield an auditable
  construction lineage.

### 8.2 What creates the gain

Discuss complete typed obligations, fail-closed routing and endpoint-tested
promotion as design components. Do not attribute the gains causally to those
components or to automatic skill discovery: current successful TSP and
OR-Debug rules are authored, and their controls do not receive matched
knowledge.

### 8.3 Construction insight

The count certificate shows that useful repair can require interacting fields.
This motivates a separating-witness teacher that organizes the same facts by
candidate change and semantic/resource obligation. The matched study is needed
before claiming that this organization improves model acquisition.

### 8.4 Relationship to external methods

BIND demonstrates the strength of answer-bearing iterative repair. CoE exposes
the difficulty of safely executing unconstrained generated programs.
OptiTrust's unavailable artifact limits local comparison. The proposed
framework can wrap another generator when its output can be compiled into the
typed contract, but compatibility does not guarantee an accuracy gain. The
indexed adapter makes this boundary concrete: reliable bounded transport is
insufficient when strict admission yields no solver-ready consensus.

## 9. Limitations and threats to validity

Cover finite verifier and grammar incompleteness, possible source-language
misinterpretation, template dependence, public-benchmark contamination,
endpoint versus full formulation equivalence, benchmark-specific skills,
retrospective mixed-router envelopes, safe-adapter undercoverage, unequal BIND
information budgets, unavailable official OptiTrust artifact, the negative
OptiTrust-style indexed method gate, exact-solver limits, closed-model
reproducibility and the negative current automatic-acquisition evidence. For
each limitation, state which narrower claim remains supported.

## 10. Conclusion

Conclude that optimization-modeling knowledge can be made more auditable by
representing it as versioned typed programs with explicit proof obligations,
selective routing and endpoint-tested promotion. The current evidence supports
multi-source methodological replication and frozen-interface composition. It
does not establish universal semantic correctness or autonomous recursive
knowledge acquisition.

## Main figures and tables

1. **Figure 1:** library transition diagram from failure through typed
   candidate, verifier/compiler, router, promotion and versioned ledger.
2. **Figure 2:** claim boundary separating declared-contract guarantees from
   empirical benchmark outcomes.
3. **Table 1:** benchmark sources, controls, groups, endpoints and information
   budgets.
4. **Table 2:** TSP and OR-Debug paired confirmation results.
5. **Figure 3:** corrections, regressions and abstentions by TSP size and
   OR-Debug structural group.
6. **Table 3:** fixed-40 BIND/CoE results with adapter and feedback columns;
   official OptiTrust marked artifact-unavailable and the indexed paper-based
   adapter reported only as a negative preflight without an accuracy row.
7. **Figure 4:** count proposer and exact version-space repair certificate.
8. **Table 4:** claim-to-proof-obligation-to-evidence-to-boundary matrix.

## Supplementary material

- formal definitions and proposition proofs;
- complete skill schemas, grammars and verifier obligations;
- TSP and OR-Debug split, promotion and confirmation hashes;
- mixed-router identity ledger;
- count-candidate enumeration and first counterexamples;
- external baseline source pins, safe-adapter coverage and failure taxonomy;
- historical V9, typed BinPacking and DCP qualification studies;
- cost, retries, unavailable outcomes and environment details; and
- data/code availability and redistribution audit.

Author names, affiliations, contributions, funding, conflicts, data/code
availability and AI-use disclosure remain author inputs. Private benchmark
bodies, request/response ledgers, credentials and evaluator-only answers must
not be released without a separate custody and redistribution review.
