# Novelty audit — finite-sample certifiable reuse

Date: 2026-09-07

Status: working literature boundary, not a claim of exhaustive priority.

## Research question being protected

Can completed historical **performance evidence** be adaptively reused in post-deployment model evaluation with a finite-sample risk certificate against current-only evaluation, while explicitly distinguishing:

1. historical mismatch;
2. weight magnitude; and
3. dependence created when the same current audit both selects borrowing and estimates current performance?

The target safety notion is MSE non-inferiority of the performance estimator, not Type-I error control, posterior robustness, or asymptotic optimality.

## Closest adjacent work and what it already occupies

### Chu & Yi, 2021 — Dynamic Historical Data Borrowing Using Weighted Average

JRSS C. Develops MSE-oriented dynamic weighting of historical and current control data and studies finite-sample operating behavior and Type-I error.

Boundary: ordinary historical-current bias–variance geometry and data-driven MSE weighting are not new here.

### Oberst et al., 2022 — Understanding the Risks and Rewards of Combining Unbiased and Possibly Biased Estimators

Studies finite-sample risk when combining a high-variance unbiased estimator with a lower-variance possibly biased estimator, including bias thresholds and transparent MSE bounds.

Boundary: the existence of a mismatch threshold for useful shrinkage is not new here.

### Li & Ignatiadis, 2025 — Prediction-Powered Adaptive Shrinkage Estimation

Introduces data-driven adaptive shrinkage and proves asymptotic optimality of risk-based tuning.

Boundary: adaptive shrinkage and risk-based weight selection are not new here.

### Mani, Xu, Lipton & Oberst, 2025/2026 — No Free Lunch: Non-Asymptotic Analysis of Prediction-Powered Inference

Provides exact finite-sample conditions under which adaptive PPI++ can be worse than gold-label-only estimation, and studies single-sample versus sample-splitting variants.

Boundary: 'estimated weights can hurt in finite samples' and 'sample splitting has a cost' are not new statements by themselves.

Important distinction to preserve: PPI is built around auxiliary predictions plus a correction structure designed for unbiased estimation; CMDO safe-reuse theory treats a completed historical performance summary as a potentially biased transport source under current deployment mismatch.

### Zhu, Yang & Wang, 2025 — Conformal Selective Borrowing for Hybrid Controlled Trials

Provides finite-sample exact randomization-based Type-I error control, post-selection validity, and adaptive threshold choice using MSE within a selective external-control framework.

Boundary: finite-sample validity after selective borrowing in general cannot be claimed as new.

Important distinction: their protected inferential target is randomization-test validity / Type-I error, whereas the present candidate theorem targets estimator-risk non-inferiority to current-only performance evaluation.

### Bayesian dynamic borrowing / SAM / elastic priors / power-prior variants

A large literature adaptively discounts historical information according to prior-data conflict and studies finite-sample bias, MSE, power, coverage or Type-I error.

Boundary: 'borrow less when conflict is larger' is deeply established and cannot support novelty.

## Candidate result that still appears distinct after this audit

The current candidate package is narrower:

1. **Magnitude-only impossibility under same-audit adaptation.** For any nontrivial cap below one, there exists a bounded estimation problem in which every fixed weight under that cap is MSE-safe, yet a data-dependent weight under the same cap is harmful.

2. **Observable high-probability risk certificate.** Under honest role separation, a finite-sample confidence set for current performance induces a worst-case mismatch coordinate `Lambda_U`; a weight chosen under the resulting cap is conditionally MSE non-inferior with probability at least `1-alpha`.

3. **Same-total-budget certifiability boundary.** When role separation spends current outcomes, a certified interval exists iff the gain available under the worst-case mismatch bound can pay the split tax: `delta <= 1/(1+Lambda_U)`.

The potentially novel object is therefore not a new shrinkage formula. It is the **certifiability boundary** linking mismatch uncertainty, same-audit dependence, and the information cost of protecting against that dependence in post-deployment performance estimation.

## Current risk to novelty

The strongest threat is Mani et al. because they combine exact finite-sample adaptive-weight analysis with sample-splitting comparisons. Any final CMDO theorem must be stated in a way that is mathematically and substantively distinct from their PPI++ setting.

The second threat is the general decision-theoretic literature on combining unbiased and biased estimators. Theorem 1 must be checked against broader admissibility / shrinkage results before any priority language is used.

## Claim language currently allowed

Allowed working language:

> We derive a finite-sample certifiability boundary for adaptive reuse of completed historical performance evidence under current deployment mismatch, separating the effect of borrowing magnitude from dependence between the borrowing rule and current-estimation noise.

Not yet allowed:

- 'first finite-sample theory of adaptive borrowing';
- 'first no-harm historical borrowing method';
- 'universal safe reuse';
- 'fail-safe';
- 'guaranteed safe under arbitrary same-audit adaptation'.

## Literature URLs used in this audit

- Chu & Yi: https://academic.oup.com/jrsssc/article/70/5/1259/7033980
- Oberst et al.: https://arxiv.org/abs/2205.10467
- Li & Ignatiadis: https://proceedings.mlr.press/v267/li25ak.html
- Mani et al.: https://arxiv.org/abs/2505.20178
- Zhu, Yang & Wang: https://proceedings.mlr.press/v267/zhu25y.html

Further priority checking is required before manuscript promotion.