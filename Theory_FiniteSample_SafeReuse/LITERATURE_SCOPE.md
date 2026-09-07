# Literature scope and novelty boundary

This note records the minimum adjacent literature that must be respected before any finite-sample safe-reuse statement is promoted into the manuscript.

## Closest known directions

1. **Dynamic historical borrowing**
   - Chu & Yi, *Dynamic Historical Data Borrowing Using Weighted Average*, JRSS C (2021).
   - Directly studies MSE-optimal weighting of historical and current information and discusses finite-sample operating behavior and Type-I error.
   - Consequence: the ordinary fixed-weight bias–variance trade-off is not a novel CMDO theorem.

2. **Prediction-Powered Adaptive Shrinkage (PAS)**
   - Li & Ignatiadis, ICML 2025.
   - Uses data-driven shrinkage and proves asymptotic optimality of its tuning strategy.
   - Consequence: adaptive shrinkage per se is not novel.

3. **No Free Lunch: Non-Asymptotic Analysis of Prediction-Powered Inference**
   - Mani, Xu, Lipton & Oberst, 2025/2026.
   - Gives exact finite-sample conditions under which adaptive PPI++ can be worse than gold-label-only estimation.
   - Consequence: 'estimated weights can hurt in finite samples' is not by itself a new result.

4. **Combining observational and experimental datasets using shrinkage estimators**
   - Existing shrinkage literature contains finite-sample risk-reduction conditions under particular models.
   - Consequence: a generic shrinkage-risk inequality must be checked carefully for prior art.

## Candidate CMDO-specific novelty, if it survives

The potentially distinct contribution is not the existence of a bias–variance trade-off. It would be one of the following:

- an exact finite-sample safety condition for **post-deployment performance reuse** in which the historical object is a completed performance estimate and the current object is a sparse outcome audit;
- a theorem that cleanly separates **weight magnitude** from **weight–error coupling**, showing why an apparently conservative adaptive weight can still reverse a fixed-use benefit;
- an implementable role-separated or otherwise dependence-controlled borrowing rule with a finite-sample guarantee against same-budget direct performance evaluation;
- a sharp impossibility statement showing that, without role separation or an explicit dependence bound, no nontrivial universal no-harm guarantee is available for same-audit adaptive reuse.

## Current status

The role-separated identity in `THEOREM_DRAFT.md` is mathematically useful but may be too close to standard random-shrinkage algebra to carry novelty by itself. Treat it as a baseline lemma.

The research value will depend on whether the next step produces either:

1. a non-oracle finite-sample certificate; or
2. a sharp same-audit impossibility + constructive safety restoration result.

Until then, do not change the frozen manuscript claim hierarchy.
