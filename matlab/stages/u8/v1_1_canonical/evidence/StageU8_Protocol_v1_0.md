# Stage U8 protocol v1.0 — certifiable natural-prevalence temporal reserve

Status before PREPARE: **freeze candidate; reserve outcomes prohibited**.

## Purpose

U6 and U7 used class-conditional balanced verified-outcome budgets and a same-block plug-in variance. U8 tests the two unresolved operational issues directly:

1. the budget counts randomly screened target cases at their natural outcome prevalence;
2. the implemented transport weight satisfies the variance-disjoint requirements of Theorem S6 on a prespecified confidence event.

U8 is a new branch under the observer programme. It neither authorizes nor modifies legacy DDO-2 Stage 12.

## Data roles frozen before reserve outcomes

| NHANES cycle | Role | Outcome access during PREPARE |
|---|---|---|
| 2011–2012 | Source training and source-only threshold | Allowed |
| 2013–2014 | Transparent historical-performance evidence | Allowed |
| 2015–2016 | Temporal reserve 1 | Prohibited |
| 2017–2018 | Temporal reserve 2 | Prohibited |
| Aug 2021–Aug 2023 | Temporal reserve 3 | Prohibited |

Only official CDC/NCHS XPT files are permitted. Mirrors and repackaged CSV derivatives are prohibited for the formal run.

## Cohort and outcome

- Adults aged at least 20 years.
- Features are taken from `DEMO`, `BMX`, `BPQ` and `SMQ` and are fixed before target outcomes.
- Outcome availability is determined only after authorized HbA1c-file access; the finite retrospective estimand is the pre-specified feature-eligible adult cohort with a released non-missing HbA1c result.
- Binary outcome: `LBXGH >= 5.7`.
- The primary criterion is fixed-threshold classification accuracy at natural prevalence.
- AUC is recorded as a supportive direct metric, not as the Theorem-S6-certified primary observer in U8 v1.0.

## Frozen model

- Ridge logistic linear classifier.
- Source cycle: 2011–2012.
- Deterministic 75/25 class-stratified source split, seed `2026080901`.
- Ridge parameter `lambda = 1e-3`.
- Continuous variables are source-median imputed, source standardized and accompanied by missing indicators.
- Categorical variables use fixed one-hot levels and an explicit missing/other level.
- Decision threshold maximizes the Youden index on the source validation split only.
- No 2013–2014 or reserve outcome tunes the model or threshold.

## Historical transport evidence

The complete 2013–2014 evaluation of the frozen source model supplies one fixed historical accuracy, `T`. It is treated as already available historical performance evidence when later cycles are audited. Its value, model, threshold and target score vectors are hashed before any reserve outcome is accessed.

## Natural-prevalence audit

- Screened-case budgets: `b = {128, 256, 512, 1024}`.
- 200 deterministic simple-random-sample replicates per reserve cycle and budget.
- Sampling is not conditioned on the target outcome and does not request fixed positive/negative counts.
- Every sampled case contributes its outcome exactly once to the full-direct estimate.
- The sample is partitioned into four equal direct folds. Opposite mapping: `1↔3`, `2↔4`.

For direct fold `q`, the observation-disjoint opposite fold supplies a two-sided Clopper–Pearson interval `[a_q,b_q]` for target correctness probability `theta`. With direct-fold size `n_q`, define

`L_q = min{a_q(1-a_q), b_q(1-b_q)} / n_q`

and

`U_q = max{(T-a_q)^2, (T-b_q)^2}`.

On the confidence event, `L_q` is no greater than the Bernoulli direct-mean variance and `U_q` is no smaller than the squared transport bias. The frozen weight is

`w_q = min{0.35, 2 L_q / (L_q + U_q)}`,

with `w_q = 0` when `L_q = 0`. The protected estimate is `(1-w_q)D_q + w_q T`; the U8 observer averages the four protected folds.

When every weight is zero, the four direct-fold means reconstruct the full same-budget direct accuracy exactly. The theorem applies to each protected fold. Cross-fold dependence prevents automatic promotion to an unrestricted aggregate theorem, so aggregate performance is evaluated empirically.

## Frozen gates

Integrity and certification:

1. three temporal reserve cycles;
2. maximum exact-fallback residual `< 1e-12`;
3. zero Eq. (S115) cap violations on covered confidence events;
4. mean simultaneous four-fold coverage `>= 0.90`;
5. minimum cycle–budget simultaneous coverage `>= 0.85`;
6. direct-error log–log slope in `[-0.70,-0.30]`.

Empirical reserve performance:

7. pooled observer MAE no greater than same-screened-budget full-direct MAE;
8. worst cycle–budget MAE regret `<= 0.005`;
9. at least two of three temporal reserve cycles improve;
10. positive mean transport weight.

All integrity/certification and empirical gates passing yields `SUPPORT_CERTIFIABLE_NATURAL_PREVALENCE_OBSERVER`. If integrity/certification passes but an efficiency gate fails, the result is retained as `PARTIAL_CERTIFICATION_SUPPORTED_EMPIRICAL_EFFICIENCY_NOT_CONFIRMED`. Any integrity/certification failure yields `FAIL_U8_INTEGRITY_OR_CERTIFICATION_GATE`. No threshold is relaxed after outcome access.

## Execution governance

1. PREPARE verifies that reserve outcome files are absent.
2. PREPARE writes and hashes code, protocol, configuration, model, historical evidence and target score vectors.
3. PREPARE stops with reserve outcomes unopened.
4. A separate authorization must reproduce the pre-outcome seal and code hashes exactly.
5. UNSEAL verifies all hashes before the first reserve outcome download.
6. The three reserve outcome files are accessed once in the frozen order.
7. After acquisition, a permanent one-shot marker is committed before any reserve outcome is read or analysed.
8. All outcomes, errors, failed gates and partial results are retained.
9. Once the marker exists, every analysis rerun is prohibited; candidate switching is also prohibited.

## Interpretation boundary

This is a retrospective emulation of representative outcome auditing across non-overlapping national survey cycles. It is stronger than overlapping within-cohort strata and directly counts screened cases, but it is not a live clinical intervention, independent hospital-team replication or proof that every possible aggregate cross-fit is risk-nonincreasing. NHANES uses a complex survey design; U8 estimates performance in the released eligible participant cohorts and does not silently claim a survey-weighted US-population estimand.
