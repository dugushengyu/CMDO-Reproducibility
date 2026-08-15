# Stage U9 Open Clinical protocol v1.0

## Scientific question

Does a frozen, outcome-audited CMDO observer retain useful and safety-bounded performance when the deployed prediction problem moves from within-dataset clinical strata and temporal survey cycles to genuinely different clinical centres or hospital systems?

The primary estimand remains fixed-threshold **natural-prevalence classification accuracy**. The comparison is between:

1. the same-budget full-direct target accuracy estimate; and
2. a guarded observer that borrows fixed historical performance evidence only when an observation-disjoint confidence event supports a non-zero transport weight.

## Observer frozen for both branches

For an audit of size `b`, sampled target cases are randomly partitioned into four equal folds. Opposite folds are `1↔3` and `2↔4`.

For protected direct fold `q`:

- `D_q` is direct accuracy in fold `q`;
- an opposite, observation-disjoint fold supplies a two-sided Clopper–Pearson interval `[a_q,b_q]` for target correctness probability `theta`;
- direct-fold variance lower bound: `L_q = min(a_q(1-a_q), b_q(1-b_q)) / n_q`;
- squared transport-bias upper bound relative to historical accuracy `T`: `U_q = max((T-a_q)^2, (T-b_q)^2)`;
- frozen guarded weight: `w_q = min(0.35, 2 L_q / (L_q + U_q))`, with `w_q=0` if `L_q<=0`.

Protected block estimate: `E_q = (1-w_q)D_q + w_q T`.

The observer is the mean of the four protected blocks. If all weights are zero, the four direct-fold means reconstruct the full same-budget direct estimate exactly. Family confidence level is `0.95`, Bonferroni-distributed across the four opposite-fold confidence events.

The blockwise certificate is not relabelled as an unrestricted theorem for the cross-fitted aggregate; aggregate MAE is assessed empirically.

---

# U9A — UCI Heart Disease multicentre bridge

## Data

Official UCI Heart Disease dataset. The four databases are Cleveland, Hungary, Switzerland and VA Long Beach. The implementation uses the standard processed 14-column versions if present in the official archive: `age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal, num`.

Outcome: `Y = 1[num > 0]`.

## Roles

Cleveland is split once, stratified and deterministically:

- 60% source training;
- 20% source threshold validation;
- 20% historical-performance evidence.

Targets are Hungary, Switzerland and VA Long Beach.

## Model

Ridge-style L2 logistic regression, numeric source-median imputation with explicit missingness indicators, source-only standardisation. The decision threshold maximises the Youden index on the Cleveland threshold-validation split only. The historical evidence `T` is fixed-threshold accuracy on the untouched Cleveland historical split.

## Auditing

Budgets: `16, 32, 64`. Replicates: `400` per target centre and budget. Sampling is simple random sampling without replacement at natural target prevalence.

## U9A bridge gates

- exact fallback residual `<1e-12`;
- zero covered-event certificate violations;
- pooled observer MAE `<=` pooled direct MAE;
- worst centre-budget MAE regret `<=0.015`;
- at least 2 of 3 target centres have non-positive pooled regret;
- positive mean transport weight.

U9A is supportive/falsifying only. Failure does not alter U9B.

---

# U9B — PhysioNet Challenge 2019 external-system reserve

## Data and roles

Official PhysioNet Challenge 2019 v1.0.0 public training data.

- `training_setA` — source hospital system;
- `training_setB` — external target hospital system.

Official documentation reports 20,336 subjects in A and 20,000 in B.

## Landmark prediction problem

Unit: one ICU subject. Features are extracted from the **first six recorded ICU hours only**.

For each physiological/laboratory variable among the first 34 Challenge variables, the source-independent raw representation contains:

- first-6-hour mean;
- last observed first-6-hour value;
- first-6-hour missing fraction.

Static/admission fields use the first record: Age, Gender, Unit1, Unit2, HospAdmTime. `ICULOS` and `SepsisLabel` are never model features.

Outcome: `Y = 1` if the subject has any `SepsisLabel=1` anywhere in the official record, otherwise `0`.

This experiment uses the dataset as a fixed clinical deployment testbed; it does not claim to introduce a new sepsis-prediction model.

## Source split and model

System A is split once, stratified and deterministically:

- 60% source training;
- 20% source threshold validation;
- 20% historical-performance evidence.

Model: L2 logistic regression with source-median imputation, missingness indicators and source-only standardisation. Threshold: Youden maximum on source threshold-validation subjects only. Historical evidence `T`: fixed-threshold accuracy on untouched source historical subjects. System B outcomes do not train, tune, recalibrate or select the model, threshold, observer or gates.

## Auditing

Budgets: `128, 256, 512, 1024`. Replicates: `200` per budget. Sampling is simple random sampling without replacement over System-B subjects at natural prevalence.

## U9B primary gates

Integrity/certification:
1. source count at least 20,000 and target count at least 19,500;
2. exact fallback residual `<1e-12`;
3. zero covered-event certificate violations;
4. mean simultaneous four-fold coverage `>=0.90`;
5. minimum budget-level simultaneous coverage `>=0.85`;
6. direct-error log–log slope in `[-0.70,-0.30]`.

Empirical performance:
7. pooled observer MAE `<=` pooled same-budget direct MAE;
8. worst budget-level MAE regret `<=0.005`;
9. mean transport weight `>0`.

Decision:
- all integrity and empirical gates pass: `SUPPORT_OPEN_EXTERNAL_CLINICAL_SYSTEM_OBSERVER`;
- integrity passes but empirical gate fails: `PARTIAL_EXTERNAL_CERTIFICATION_EFFICIENCY_NOT_CONFIRMED`;
- integrity fails: `FAIL_U9B_INTEGRITY_OR_CERTIFICATION_GATE`.

## Claim boundary

U9B is an external-system retrospective reserve. It is stronger than within-cohort subgrouping and does not depend on eICU access. It is not a prospective intervention, a randomised clinical trial or a claim that transport borrowing must improve every metric or every deployment.

The eICU programme remains a deferred independent multicentre confirmation.
