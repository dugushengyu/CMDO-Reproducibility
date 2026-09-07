# Manuscript reframing trigger

This branch must not create an endless sequence of incremental manuscript upgrades. The current submission manuscript remains the baseline unless the theory crosses the threshold below.

## Do NOT reframe the manuscript if the branch ends with only

- the ordinary fixed-weight bias–variance identity;
- the role-separated safe cap `2/(1+Lambda)`;
- a post-completion explanation of U10 coupling;
- another simulation showing that adaptive weights can hurt;
- a certificate that is formally valid but operationally vacuous at realistic budgets.

Those are useful supporting results, but they would be additive rather than identity-changing.

## Reframe PRESERVE if both A and B are established

### A. Structural impossibility

A general theorem establishes that no non-zero borrowing-magnitude cap alone can guarantee MSE non-inferiority under unrestricted same-audit adaptation, even when every fixed weight under the same cap is non-inferior.

Current status: **proved in THEORY_RESULT_V1, pending literature audit**.

### B. Constructive finite-sample certifiability

An observable, non-oracle certificate is proved from current evidence, with a clearly stated finite-sample probability guarantee and without target-truth leakage.

Current status: **proved under honest role separation in THEORY_RESULT_V1; operational non-vacuity remains unresolved**.

## Reframe the whole paper only if C is also established

### C. Same-total-budget boundary with practical content

Either:

1. the full-budget certifiability boundary is shown to be non-vacuous for a meaningful range of realistic deployment states; or
2. a stronger impossibility result shows that the safety–information trade-off itself is fundamental, and a dependence-controlled construction is provided that materially reduces the simple split tax.

Current status: **analytic boundary proved; simple exact-confidence-set split appears potentially too conservative and requires explicit probe**.

## Potential revised novelty if A+B+C survive

The paper would no longer end at the statement that fixed-use evidence value can be lost under adaptation. The final novelty would become:

> Post-deployment evaluation has an evidential order, and adaptive historical evidence has a finite-sample certifiability boundary: magnitude control alone cannot guarantee safe reuse under same-audit adaptation; finite-sample certification becomes possible only when the information supporting reuse is separated or otherwise dependence-controlled, and only when the certified historical-information gain is large enough to pay the information cost of that protection.

This would turn PRESERVE from a failure diagnosis into an impossibility/possibility theory.

## Stop rule

If the non-oracle full-budget certificate is vacuous over realistic regimes and no sharper dependence-controlled construction can be proved, do not reopen the manuscript narrative. Keep the result as a theory note / Supplementary possibility boundary and submit the existing manuscript.