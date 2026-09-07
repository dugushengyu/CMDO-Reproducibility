# Novelty audit v2 — finite-sample certifiability boundary

Date: 2026-09-07

Status: targeted priority audit, not a claim of exhaustive global priority.

## Protected question

The candidate contribution is **not** dynamic borrowing, adaptive shrinkage, bias–variance weighting, finite-sample failure of estimated weights, sample splitting, or historical-bias control by themselves.

The protected question is narrower:

> In post-deployment performance estimation, when a completed historical performance value may be transport-biased and a sparse current outcome audit is the only direct current evidence, can adaptive reuse be certified in finite samples against current-only evaluation, and what information-theoretic price is paid when the same audit cannot safely serve both weight selection and current estimation?

The safety target is MSE non-inferiority of the current-performance estimator.

## Closest prior work and occupied territory

### Chu & Yi (2021), Dynamic Historical Data Borrowing Using Weighted Average, JRSS C

- MSE-oriented historical/current weighting.
- Finite-sample operating characteristics and Type-I error considerations.
- Occupied territory: ordinary fixed/dynamic historical borrowing and its bias–variance trade-off.

### Rosenman, Basse, Owen & Baiocchi (2023), Combining Observational and Experimental Datasets Using Shrinkage Estimators, Biometrics, DOI 10.1111/biom.13827

- Combines an unbiased high-quality estimate with a possibly biased lower-variance source.
- Proves finite-sample conditions under which proposed shrinkage estimators improve risk over the experimental-only estimator.
- Occupied territory: finite-sample risk improvement from biased/unbiased estimator combination is not new.

### Oberst et al. (2022/2023), risks/rewards of combining unbiased and possibly biased estimators

- Transparent risk thresholds and bounded-risk behavior in the scalar data-combination problem.
- Occupied territory: existence of a bias threshold for useful shrinkage is not new.

### Li, Lin, Huang, Tian & Zhu (2023), A frequentist approach to dynamic borrowing, Biometrical Journal, DOI 10.1002/bimj.202100406

- Frequentist dynamic borrowing via adaptive lasso.
- Explicitly notes that strict finite-sample Type-I control can force zero borrowing and hence eliminate power gain in worst cases.
- Occupied territory: the generic safety–power tension in dynamic borrowing is not new.

### Li & Ignatiadis (2025), Prediction-Powered Adaptive Shrinkage Estimation, ICML

- Data-driven shrinkage using an unbiased risk estimate and correlation-aware risk estimation.
- Asymptotic optimality of tuning.
- Occupied territory: adaptive shrinkage and correlation-aware risk estimation are not new.

### Mani, Xu, Lipton & Oberst (2025/2026), No Free Lunch: Non-Asymptotic Analysis of Prediction-Powered Inference

- Exact finite-sample conditions for when adaptive PPI++ improves or worsens gold-label-only mean estimation.
- Direct discussion of same-sample and sample-splitting variants.
- Occupied territory: finite-sample adaptive-weight harm and sample-splitting cost are not new in general.
- Major threat: any CMDO result must remain substantively distinct from the PPI correction structure.

### Zhu, Yang & Wang (2025), Enhancing Statistical Validity and Power in Hybrid Controlled Trials, ICML

- Finite-sample exact randomization-based Type-I error control after selective external-control borrowing.
- Conformal selection and MSE-based threshold adaptation.
- Occupied territory: finite-sample post-selection validity in external borrowing is not new.

### Armstrong, Kline & Sun (2025), Adapting to Misspecification, Econometrica, DOI 10.3982/ECTA21991

- Studies robust-versus-efficient estimators when the restricted estimator can be biased.
- Constructs adaptive minimax estimators when the bias bound is unknown.
- Occupied territory: adapting shrinkage to an unknown misspecification bound is not new.

### Sawada, Nomura & Shinozaki (2026), Dynamic Borrowing With a Bias-Tolerance Cap in Augmented Randomized Controlled Trials, Statistics in Medicine, DOI 10.1002/sim.70473

- Dynamically borrows external controls while controlling expected bias below a prespecified tolerance cap.
- Occupied territory: a borrowing cap justified by bias control is not new.

### Broader Stein / model-averaging / empirical-Bayes literature

- Includes exact or asymptotic dominance results for combining unbiased and biased estimators, sometimes with estimated weights and dependence structures.
- Occupied territory: generic estimator averaging and dominance cannot carry the novelty claim.

## Result that remains distinct after the targeted audit

No paper located in this audit directly matches the following combined theorem package:

1. **Same-audit magnitude-only impossibility:** even when *every fixed convex weight* toward a completed historical value is MSE-beneficial, for every positive cap `omega<=1` there exists a same-audit data-dependent rule taking only `0` and `omega` that is MSE-harmful.

2. **Post-deployment performance certificate:** an independent current decision audit induces an observable worst-case historical-mismatch bound and hence a finite-sample high-probability conditional MSE certificate for reuse of a completed historical performance summary.

3. **Same-total-budget feasibility boundary:** when the decision audit is withheld from evaluation to create independence, full-budget non-inferiority exists only if the mismatch uncertainty can pay the resulting information cost.

4. **One-decision-standard-error boundary:** in the iid sample-mean case, no role-separated convex weight can beat the full-budget current-only estimator unless `|H-theta| <= SD(D_decision)`. The maximally tolerant weight is exactly the fraction of the total audit spent on the decision sample.

5. **Gaussian certification-power ceiling:** under exact Gaussian decision-audit sampling, any level-`alpha` certification rule for this full-budget-safe region has a sharply bounded certification probability even at perfect historical agreement; at `alpha=0.05`, the maximum is about 8.23%.

The object is therefore a **certifiability trilemma** linking:

- same-audit dependence;
- historical mismatch;
- and the current-information cost required to make reuse certifiable against a fair full-budget direct benchmark.

## Why this is not just a restatement of Mani et al.

Mani et al. analyze PPI/PPI++ mean estimation, where auxiliary predictions enter a correction structure intended to preserve the target estimand. The present setting treats a *completed historical performance estimate* as a potentially biased transport source. The new v2 boundary is driven by the need to learn whether that historical performance is close enough to the current deployment truth while preserving a fair same-total-outcome comparator.

The exact one-decision-standard-error limit and the corresponding certification-power ceiling are specific consequences of that historical-reuse/full-budget comparison and were not located in the PPI finite-sample analysis during this audit.

## Why this is not a bias-cap paper

Sawada et al. protect expected estimator bias under a prespecified tolerance. The CMDO candidate target is MSE non-inferiority relative to current-only performance evaluation. Bias control does not imply MSE no-harm, and the v2 theorem explicitly includes the variance/information cost of generating an independent borrowing decision.

## Why this is not ordinary minimax adaptation

Armstrong et al. optimize worst-case risk relative to a misspecification oracle under a bias-bound framework. The present result instead asks whether a *finite current audit can certify* that historical reuse is no worse than using that entire audit directly, and shows that the act of creating independent evidence for that certification constrains the safely tolerable mismatch to one decision-audit standard error in the iid mean model.

## Claim language currently supportable

Working claim:

> We derive a finite-sample certifiability boundary for adaptive reuse of completed historical performance evidence in post-deployment evaluation. Magnitude control alone cannot guarantee no-harm under unrestricted same-audit adaptation; honest role separation restores a finite-sample certificate but imposes an information cost that limits full-budget-safe historical mismatch to one decision-audit standard error in the iid mean problem, making high-confidence certification intrinsically low-power in a Gaussian benchmark.

Do **not** claim:

- first finite-sample theory of adaptive borrowing;
- universal impossibility for every possible data-fusion estimator;
- universal no-harm;
- first bias cap;
- first sample-splitting result;
- first adaptive shrinkage safety result.

## Current novelty verdict

**Promising and plausibly identity-changing, but narrowly framed.**

The targeted literature search found close work on every ingredient separately, but did not locate a direct prior theorem combining same-audit magnitude-only impossibility with a fair full-budget role-separation boundary and a finite-sample/high-confidence certifiability limit for completed historical performance reuse.

Before submission-level priority language, one further specialist audit should target older model-averaging/admissibility results and exact equivalence-testing theory. Even if those literatures contain analogous mathematical lemmas, the post-deployment performance-reuse synthesis may remain novel at the problem/architecture level; priority should then be claimed for the combined certifiability framework rather than for each algebraic lemma.