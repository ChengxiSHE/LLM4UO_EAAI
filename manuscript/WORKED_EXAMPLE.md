# Worked example: one proof-carrying TSP skill

Status: synthetic explanatory example, 2026-10-15. This example contains no
benchmark record, evaluator-only answer, request or response body. It is not
part of any reported accuracy denominator.

## Public task

Consider a complete undirected graph on nodes `A`, `B`, `C`, and `D` with
costs:

| Edge | AB | AC | AD | BC | BD | CD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cost | 1 | 2 | 4 | 4 | 2 | 1 |

The public task asks for a minimum Hamiltonian cycle subject to two additional
relations:

1. edge `AB` is forbidden; and
2. exactly one of edges `AC` and `CD` must be present.

The example is deliberately small enough to enumerate. Fixing `A` as the start
and identifying a tour with its reverse leaves three cycles:

| Cycle | Cost | Avoids AB | XOR(AC, CD) | Typed contract passes |
| --- | ---: | ---: | ---: | ---: |
| A-B-C-D-A | 10 | no | yes | no |
| A-B-D-C-A | 6 | no | no | no |
| A-C-B-D-A | 12 | yes | yes | yes |

The canonical unconstrained TSP controller therefore chooses cost 6, but that
tour violates both additional relations. The typed skill chooses the only
contract-valid cycle, with cost 12. This difference illustrates formulation
correctness: a lower objective is not evidence of correctness when the model
omits public constraints.

## Skill artifact

The public guard requires a complete graph, one well-formed forbidden edge and
two distinct present edges for the exclusive-or relation. The evidence
extractor emits the inert contract

```text
nodes       = [A, B, C, D]
forbidden   = {A, B}
xor_edges   = [{A, C}, {C, D}]
objective   = minimum closed-tour cost
```

For directed arc variables `x[i,j]`, the trusted compiler first emits the
canonical exactly-one in/out and subtour-elimination constraints. It then
defines the undirected-use indicator `u[i,j] = x[i,j] + x[j,i]` and adds

```text
u[A,B] = 0
u[A,C] + u[C,D] = 1
```

The semantic certificate checks that the forbidden-edge and XOR relations in
the typed contract are represented exactly. The resource certificate counts
the emitted variables, rows, nonzeros and serialized bytes before solver
execution. A failed parse, ambiguous guard, failed certificate, resource
overflow, solver failure or invalid projected tour returns a declared failure
or the pinned previous-library output; no check may be silently dropped.

## What each layer proves

| Layer | Established for this example | Not established by this layer |
| --- | --- | --- |
| Public guard and extraction | The input is represented by the displayed typed contract | That arbitrary natural language is always interpreted faithfully |
| Trusted compilation | The emitted model contains the declared TSP, forbidden-edge and XOR constraints | That the declaration itself matches an unseen author's intent |
| Exact solution and projection | The returned cycle is optimal for the compiled typed contract | Population benchmark accuracy |
| Frozen endpoint | The returned cycle can be scored under a prespecified task rule | Universal semantic equivalence |
| Promotion | Paired held-out outcomes can decide whether the skill enters the library | Distribution-free non-regression |

The example also clarifies producer independence. A human, BIND, CoE, another
LLM or finite enumeration may propose the displayed artifact. The unchanged
compiler and verifier should make the same admission decision for identical
artifact bytes. Proposal source can affect discovery efficiency, but it does
not redefine correctness.
