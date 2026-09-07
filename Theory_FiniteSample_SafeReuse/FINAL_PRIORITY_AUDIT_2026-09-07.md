# Final targeted priority audit — certifiable historical performance reuse

Date: 2026-09-07

Status: targeted literature audit for manuscript framing; not a claim of exhaustive global priority.

## Bottom line

The branch should **not** claim novelty for any individual generic ingredient: fixed-weight shrinkage, biased/unbiased estimator averaging, data-dependent weights, dynamic historical borrowing, sample splitting, cross-fitting, equivalence testing, or finite-sample validity after selective borrowing.

The defensible candidate novelty is the **combined certifiability architecture for completed historical performance evidence in post-deployment evaluation**.

## What the literature clearly already contains

1. **Stein / empirical-Bayes / model-averaging dominance.** Exact and asymptotic risk improvements from shrinking or averaging an unbiased estimator toward a biased/restricted estimator are classical, including structured data-dependent weights. Therefore neither the baseline risk identity nor the existence of useful shrinkage is new.

2. **Finite-sample biased/unbiased data fusion.** Modern work such as Rosenman et al. proves finite-sample conditions under which combining experimental and possibly biased observational estimates reduces risk. Therefore a finite-sample MSE improvement condition by itself is not new.

3. **Adaptive dynamic historical borrowing.** Bayesian and frequentist literatures already adapt borrowing to prior/current-data conflict and study bias, MSE, power, coverage, and Type-I error. Therefore `borrow less under mismatch` is established territory.

4. **Finite-sample failure of estimated adaptive weights.** Recent prediction-powered-inference work derives non-asymptotic conditions under which adaptive weighting can lose to current/gold-only estimation, including comparisons involving sample splitting. Therefore `adaptive weights can hurt` is not new in isolation.

5. **Finite-sample selective-borrowing validity.** Selective external-control methods already provide exact finite-sample inferential validity in specific designs. Therefore `finite-sample validity after borrowing` cannot be claimed broadly as new.

6. **Equivalence testing and optimal tests.** Testing whether an unknown parameter lies within a predeclared interval is classical. Uniformly/most-powerful and finite-sample equivalence procedures are well developed. Consequently the Gaussian central-region calculation in `THEORY_RESULT_V2.md` should be treated as a **derived calibration consequence of the one-standard-error boundary**, not as a standalone new statistical testing theorem.

7. **Cross-fitting itself is not a novelty.** The exact cross-fit identity in `CROSSFIT_CLOSURE.md` is useful because it closes an obvious proposed repair in this CMDO architecture, but it should not be advertised as the first observation that cross-fitting can retain dependence or fail to dominate.

## Closest threats to the final claim

### Rosenman et al., Biometrics 2023

Closest on finite-sample risk improvement when combining an unbiased high-quality estimate with a possibly biased source. The distinction we must preserve is that CMDO asks whether a *completed historical performance summary* can be certified for reuse against current-only post-deployment evaluation under a sparse current-outcome budget, with the same current outcomes potentially serving both adaptation and evaluation roles.

### Mani et al., 2025/2026, non-asymptotic PPI

Closest on finite-sample adaptive-weight failure and sample-splitting costs. The distinction is substantive: PPI's auxiliary predictions enter an unbiased correction architecture, whereas CMDO's historical performance summary can carry transport mismatch `B=H-theta`. The CMDO full-budget boundary arises from having to establish whether that historical performance is close enough to current deployment truth while preserving the current outcomes that direct evaluation could have used.

### Armstrong, Kline & Sun, Econometrica 2025

Closest on adaptation to an unknown misspecification bound and robustness-efficiency trade-offs. The distinction is that the CMDO result is a finite-current-evidence **certifiability** question against a same-total-budget direct benchmark, with an explicit information cost for separating evidence roles.

### Dynamic borrowing / bias-cap literature

Closest on external/historical information reuse and protecting against prior-data conflict. The protected target differs: the proposed CMDO result is MSE non-inferiority of a current-performance estimator, not merely a bias tolerance, Type-I error target, posterior robustness criterion, or asymptotic borrowing consistency.

## Protected theorem package after the audit

The strongest defensible package is:

### A. Same-audit magnitude-only limitation

For every positive cap `omega<=1`, there exists a bounded scalar problem in which **every fixed convex weight** toward the historical value improves MSE, yet a same-audit data-dependent rule using only `0` and `omega` is harmful.

Do not sell the fact that arbitrary data dependence can be harmful as a new universal statistical principle. Its role is to establish that a `safe borrowing cap` cannot by itself complete the PRESERVE stage.

### B. Observable finite-sample possibility under role separation

An independent current decision audit can turn a finite-sample confidence set for current performance into a conditional high-probability MSE certificate for historical reuse, without target-truth leakage.

Again, confidence-set inversion is not novel by itself. Its role is constructive: it shows what extra evidential condition restores certifiability once same-audit magnitude control fails.

### C. Same-total-budget information boundary

When the independent decision audit is drawn from the same finite outcome budget that direct evaluation could otherwise use, a certified reuse interval exists only when historical mismatch is small enough to compensate for the variance/information lost to role separation.

In the iid mean problem this collapses to the particularly transparent boundary

`|H-theta| <= SD(D_decision)`.

This **one-decision-standard-error boundary**, in conjunction with A and B, is the strongest candidate for a distinct theoretical contribution.

### D. Cross-fit closure

Symmetric two-fold cross-fitting does not automatically eliminate the problem: an exact full-budget risk identity retains the term `a=E[We]`, and a bounded example has individually role-separated fold estimators but 29% higher aggregate risk than full-data direct evaluation.

This closes a natural repair route and strengthens the interpretation that the issue is not solved merely by relabelling same data into folds.

### E. Calibration consequence

Once C produces a one-standard-error equivalence region, classical equivalence-testing theory implies that high-confidence certification can have low power. The 8.23% Gaussian value is a useful quantitative consequence and explanation of the failed naive split probe, **not** a priority claim for a new equivalence test.

## Final novelty language judged defensible

> We identify a finite-sample certifiability boundary for reuse of completed historical performance evidence in post-deployment evaluation. A bound on borrowing magnitude alone cannot protect unrestricted same-audit adaptation; independent current evidence can restore a conditional risk certificate, but when that evidence is drawn from the same finite outcome budget, the act of creating independence consumes information that direct evaluation would otherwise use. In the iid mean problem, this limits full-budget-safe historical mismatch to one decision-audit standard error, and ordinary symmetric cross-fitting does not in general remove the resulting aggregate dependence.

This is narrower than `first finite-sample adaptive borrowing theory` and is the claim that best survives the targeted literature audit.

## Priority verdict

**No direct prior work was located in the targeted searches that states this complete post-deployment-performance certifiability package.** This is not proof of global priority. Older shrinkage/model-averaging and equivalence-testing literatures contain close mathematical ingredients, so manuscript priority language should attach to the **combined certifiability boundary and evidential role architecture**, not to each lemma separately.

## Manuscript implication

The theory is now strong enough to justify a controlled rewrite of PRESERVE if local verification passes. It should **replace** part of the existing post-hoc mechanism narrative rather than be appended after it. IDENTIFY and REUSE do not need a new fourth stage; PRESERVE becomes the stage that asks not only whether adaptive reuse loses fixed-use value, but whether preservation can be certified from the finite current evidence available.