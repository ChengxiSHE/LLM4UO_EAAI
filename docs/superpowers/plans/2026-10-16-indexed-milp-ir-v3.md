# Indexed MILP IR v3 implementation plan

**Goal:** close the v2 long-generation failure with a generic bounded IR and
produce a scoreable, independently audited common-38 sensitivity.

1. Implement and test the pure IR validator, expression evaluator, finite set
   expander, linear compiler and proof-carrying resource certificate.
2. Demonstrate expressivity with authored RCPSP and VRPTW fixtures while
   mechanically proving that the interpreter contains no family routing or
   current-skill dependency.
3. Replace the canonical-candidate and typed-review contracts with hash-bound
   IR objects; treat unavailable reviews as abstentions.
4. Add an OpenAI/httpx transport worker executed from the supplied preparation
   environment, retaining the existing durable request ledger and three-send
   cap.
5. Freeze a worst-shape answer-blind capacity gate.  Preserve the failed
   2,048-token v1 gate and test a clean 3,072-token v2 gate.  Do not dispatch
   common-38 unless every canonical request passes.
6. If the gate passes, freeze and run a clean common-38 plan from scratch,
   publish a body-free full-denominator result, independently reconstruct it,
   and update the paper evidence chain.  Never reuse v2 responses.
