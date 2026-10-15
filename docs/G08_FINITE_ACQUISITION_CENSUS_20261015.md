# G08 finite active-acquisition census

Status: **complete for the frozen finite semantic-class population**.

The 64-member typed grammar contains 32 distinct semantic candidates after the
resource-policy axis is removed. On the complete 20,977-query verification
domain, those candidates induce 10 extensionally distinguishable semantic
classes. This census treats those 10 classes as the complete target population.

Both acquisition policies begin with all 10 classes and observe only the label
of a selected assignment query. The balanced policy selects the query that
minimizes the largest remaining partition; the control selects the first
separating query in the same frozen order. Neither policy receives an authored
fact statement or the hidden target identity.

| Policy | Identified within 3 queries | Total queries | Mean | Worst |
|---|---:|---:|---:|---:|
| Balanced separating witness | 10/10 | 26 | 2.6 | 3 |
| Canonical first witness | 6/10 | 30 | 3.0 | 4 |

The paired budget outcome is 4 balanced-only,
0 control-only, 6 both
and 0 neither. Because every class is enumerated,
these are exact finite-population quantities rather than sampling estimates.

This closes a bounded acquisition claim: balanced verifier-selected witnesses
automatically identify every extensional skill class within the frozen grammar
and budget, whereas the fixed-order control identifies six. It does not show
natural-language fact discovery, identify the resource-policy axis, estimate
LLM proposer efficacy, improve benchmark accuracy or promote a library.
