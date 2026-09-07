# Initial findings from frozen U10 summaries

Status: post-completion exploratory analysis only.

Using the frozen U10 target accuracies, historical accuracy, cohort sizes and audit budgets, we computed the finite-population direct-accuracy variance

`V = theta(1-theta)(N-m) / [m(N-1)]`

and the oracle role-separated cap

`omega_safe = min(1, 2/(1 + B^2/V))`.

The observed shared-adaptive mean weights and frozen matched-fixed/adaptive gains are:

| cohort | budget | mean shared weight | oracle role-separated cap | matched-fixed MSE gain | shared-adaptive MSE gain |
|---|---:|---:|---:|---:|---:|
| Georgia | 128 | 0.316186 | 1.000000 | +45.62% | +30.92% |
| Georgia | 256 | 0.281175 | 0.665498 | +32.28% | +15.37% |
| Georgia | 512 | 0.224879 | 0.390967 | +14.96% | -11.37% |
| Georgia | 1024 | 0.132221 | 0.206489 | +15.03% | -10.32% |
| CPSC 2018 | 128 | 0.273988 | 0.604108 | +33.33% | +10.20% |
| CPSC 2018 | 256 | 0.201129 | 0.350221 | +21.32% | -8.54% |
| CPSC 2018 | 512 | 0.120396 | 0.185180 | +4.23% | -19.37% |
| CPSC 2018 | 1024 | 0.053968 | 0.089625 | +11.04% | -3.16% |

## Immediate implication

All **8/8** observed mean shared weights lie below the oracle cap that would be sufficient under role-separated independence. Yet the frozen shared-adaptive rule is harmful relative to full direct evaluation in **5/8** states, while the matched constant-mean-weight comparator is beneficial in **8/8** states.

This is a strong diagnostic for the draft theory:

- conservative weight magnitude alone does not explain or prevent the adaptive failures;
- the role-separation/independence assumption in Proposition A is substantive;
- the coupling correction in Proposition B is not optional bookkeeping: it is exactly the kind of term needed to explain why a below-cap adaptive rule can still reverse a fixed-use benefit.

This does **not** yet prove a prospective safe-reuse rule. The cap above is oracle because `B` uses revealed target truth. It also does not remove the full-budget split-tax problem if decision and evaluation outcomes are separated.

## Research decision after this first probe

The direction is worth continuing. The most promising next target is not another simulation or dataset. It is to derive a non-oracle finite-sample certificate, or else prove a sharp impossibility statement for unrestricted same-audit adaptation and show what minimal role separation/dependence control restores a guarantee.
