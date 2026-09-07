# Manuscript reframing trigger — v2 status

This branch must not create an endless sequence of incremental manuscript upgrades. The current submission manuscript remains the frozen baseline unless the theory changes the scientific identity of PRESERVE.

## Do NOT reframe the manuscript for additive results only

Do not reopen the paper merely for:

- the ordinary fixed-weight bias–variance identity;
- the role-separated cap `2/(1+Lambda)`;
- a post-completion explanation of U10 coupling;
- another simulation showing that adaptive weights can hurt;
- sample splitting by itself;
- a formally valid but operationally vacuous certificate.

Those would be supporting material, not a new novelty identity.

## Threshold A — structural same-audit impossibility

Required result:

> a general theorem showing that borrowing-magnitude control alone cannot guarantee finite-sample MSE no-harm under unrestricted same-audit adaptation, even when all corresponding fixed weights are safe.

**Status: passed.** `THEORY_RESULT_V2.md` gives a bounded construction valid for every `0<omega<=1`, and in that construction every fixed convex weight `0<w<=1` is beneficial while the same-audit `{0,omega}` rule is harmful.

## Threshold B — constructive finite-sample possibility

Required result:

> an observable non-oracle finite-sample certificate based on current evidence, with no target-truth leakage.

**Status: passed in principle, but not as a practical full-budget method.** Honest role separation plus a finite-sample confidence set yields a `1-alpha` conditional MSE certificate relative to evaluation-only direct estimation.

## Threshold C — fair same-total-budget boundary

Required result:

> a theorem characterizing when the protection mechanism itself destroys the information gain needed to beat a direct estimator using the full current-outcome budget.

**Status: passed analytically.** In the iid sample-mean problem, full-budget role-separated convex reuse is feasible iff historical bias lies within one decision-audit standard error. The maximally tolerant weight is `w=m_s/M`.

## Threshold D — demonstrate that the boundary is scientifically consequential, not a quadratic curiosity

Required result:

> show that high-confidence certification of the full-budget-safe region is genuinely information-limited.

**Status: passed in a canonical benchmark.** In the exact Gaussian decision-audit model, every level-5% certification rule has perfect-match certification probability at most about 8.23%. The simple exact-binomial 95% confidence-set construction also had zero trigger probability across the U10-like probe grid.

## Current manuscript decision

The branch has now crossed the **scientific reframing threshold** for PRESERVE. The remaining question is editorial/architectural, not whether another theorem is needed:

> Can the certifiability trilemma replace and deepen the existing PRESERVE theory without introducing a fourth conceptual stage or overwhelming the main text?

If yes, reopen the manuscript and rewrite PRESERVE around the finite-sample certifiability boundary.

If no, keep v2 as a Supplementary/theory note and submit the current manuscript unchanged.

## Protected revised novelty

If integrated, the novelty should be framed as:

> Post-deployment evaluation has an evidential order. After current performance becomes identifiable and historical evidence is shown to have fixed-use value, adaptive reuse faces a finite-sample certifiability boundary: magnitude control alone cannot protect same-audit adaptation, while creating independent evidence for safety consumes current-outcome information and can make fair full-budget reuse statistically uncertifiable.

This is an upgrade of **PRESERVE**, not a fourth stage.

## Priority-language constraint

Even after integration, do not claim:

- the first finite-sample theory of adaptive borrowing;
- the first historical-borrowing safety result;
- universal impossibility for all data-fusion estimators;
- universal no-harm.

The defensible novelty is the combined certifiability boundary for completed historical performance evidence in post-deployment evaluation.