# Stage U9 protocol v1.0

## Sealed multicentre decision observability in eICU-CRD

**Status:** frozen implementation protocol supplied before any U9 reserve outcome is analyzed.  
**Stage:** U9.  
**Protocol identifier:** `SEALED_MULTICENTRE_DECISION_OBSERVABILITY_RESERVE`.  
**Primary code:** `CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0.m`.  
**Data source:** eICU Collaborative Research Database v2.0.

## 1. Scientific question

Can a guarded historical observer make a fixed deployment-performance decision observable with fewer screened patients across genuinely distinct hospitals, while preserving exact fallback to the direct audit and preventing false assurance when historical transport fails?

U9 is designed as the multicentre bridge between controlled validation and a decision-facing clinical deployment claim. It treats hospitals—not random patient splits—as the deployment units. Twenty hospitals are placed in a sealed reserve before their outcomes are read by the analysis phase.

## 2. Data access and governance

eICU-CRD v2.0 is a credentialed PhysioNet resource. The runner is responsible for completing the required training and data-use agreement and for keeping official and row-level derived data local. The package contains no eICU records.

Official documentation:

- Dataset and access: <https://physionet.org/content/eicu-crd/2.0/>
- Table documentation: <https://eicu.mit.edu/eicutables/apachepatientresult/>
- Patient table: <https://eicu.mit.edu/eicutables/patient/>
- Hospital table: <https://eicu.mit.edu/eicutables/hospital/>

Only three official tables are read: `patient`, `apachePatientResult`, and `hospital`. The adapter stores raw IDs, row-level outcomes, and outcome-free target scores only inside the local working directory. The canonical ZIP excludes all row-level records and raw identifiers.

## 3. Cohort and hospital eligibility

The adapter applies all eligibility rules before examining reserve outcomes:

1. Adult patients, age ≥18 years; the eICU `> 89` age code is represented as 90.
2. First ICU visit (`unitVisitNumber = 1`).
3. One record per `uniquePID`, keeping the earliest eligible `patientUnitStayID`.
4. A finite APACHE IVa predicted hospital-mortality score in [0,1].
5. One deterministic APACHE IVa row per stay.
6. Hospitals with at least 512 outcome-free score-eligible cases.

Exactly 38 eligible hospitals are sampled by frozen seed 2026081001. Outcome-free roles are assigned in the sampled order: six source, six historical, six calibration, and twenty reserve hospitals. Pseudonyms `H001`, `H002`, … are based on the sorted selected raw hospital IDs, independently of role and outcome.

Any reserve hospital with fewer than 256 finite outcomes after authorized opening is not evaluable. The primary integrity gate requires all twenty reserve hospitals to remain evaluable; the design is not relaxed after reveal.

## 4. Physical outcome separation

The official APACHE result table contains both `predictedHospitalMortality` and `actualHospitalMortality`. U9 therefore uses a custodian-style adapter before the analysis seal:

- `StageU9_OutcomeFree_Roster_v1_0.csv`: score, covariates, hospital pseudonym, and role; no outcome.
- `StageU9_Development_Outcomes_v1_0.csv`: source, historical, and calibration outcomes.
- `StageU9_RESERVE_OUTCOME_VAULT_v1_0.csv`: reserve outcomes only.
- `StageU9_RESTRICTED_Hospital_And_Case_Mapping_v1_0.csv`: local raw-to-pseudonym mapping.

The adapter computes and prints no reserve prevalence or performance statistic. It records SHA-256 hashes of every official input and every split output. A third-party custodian running `ADAPT` provides the strongest separation; a single-machine run still enforces physical files, code paths, immutable hashes, and a permanent one-shot marker.

## 5. Frozen operating point and primary estimand

The source hospitals alone select a threshold for the APACHE IVa mortality score by maximizing Youden’s J. That threshold is applied unchanged everywhere.

For reserve hospital (h), let (Y_{hi}\in\{0,1\}) be hospital mortality, (S_{hi}\in[0,1]) the APACHE IVa score, and

\[
Z_{hi}=\mathbf{1}\{\mathbf{1}(S_{hi}\ge t)=Y_{hi}\}.
\]

The primary hospital estimand is natural-prevalence fixed-threshold accuracy

\[
\theta_h=\mathbb{E}(Z_{hi}\mid h).
\]

No prevalence balancing or case-control reweighting is used for the primary result.

The primary acceptance floor (c) is the median of hospital-specific fixed-threshold accuracies in the six historical hospitals. A reserve hospital is truly acceptable when (θ_h ≥ c), and truly unacceptable otherwise. Estimated decisions use a prespecified guard band:

- acceptable if \(\widehat\theta_h\ge c+0.01\);
- unacceptable if \(\widehat\theta_h\le c-0.01\);
- unresolved otherwise.

Historical 25th- and 75th-percentile floors are retained for criterion-sensitivity summaries only.

## 6. Audits and frozen witnesses

For each reserve hospital, 200 nested audit permutations are drawn with seed

\[
2026081002 + 1000003h + 7919r \pmod{2^{31}-1},
\]

where (h\) is the ordered reserve-hospital index and (r\) the replicate. The first 64, 128, and 256 cases in each permutation define nested screened-case budgets.

The primary direct estimate is the audit mean \(\bar Z\). U9 compares it with:

1. **Static history:** a convex combination of the audit mean and pooled historical accuracy. Its weight is selected from {0,0.05,…,0.35} using calibration hospitals only.
2. **ATC-style telemetry:** source-fitted confidence thresholding without target outcomes; conceptually based on Average Thresholded Confidence (Garg et al., 2022, <https://arxiv.org/abs/2201.04234>).
3. **PPI++-style mean correction:** a frozen source/history correctness proxy plus an audit-estimated clipped correction coefficient; conceptually based on prediction-powered inference (Angelopoulos et al., 2023, <https://arxiv.org/abs/2311.01453>).
4. **CMDO guarded observer:** blockwise historical transport that withdraws toward the exact direct audit when transport cannot be certified.

Comparator names are deliberately marked “style” where the implementation targets the relevant operational idea rather than claiming identity with every procedure in the cited paper.

## 7. Guarded observer and exact fallback

Each audit budget is divided into four equal folds. For fold (q), a disjoint opposite fold supplies a two-sided Clopper–Pearson interval \([\ell_q,u_q]\) for \(\theta_h\), with familywise allocation \(\delta_q=0.05/4\). The direct fold supplies \(D_q\), and historical accuracy is (a_H).

Define a variance lower bound and squared-transport-bias upper bound

\[
L_q=\frac{\min\{\ell_q(1-\ell_q),u_q(1-u_q)\}}{n_q},\qquad
U_q=\max\{(a_H-\ell_q)^2,(a_H-u_q)^2\}.
\]

The frozen transport weight is

\[
w_q=\min\left(0.35,\frac{2L_q}{L_q+U_q}\right),
\]

with (w_q=0) when (L_q\le0\). The fold estimate is

\[
E_q=(1-w_q)D_q+w_qa_H,
\]

and the hospital estimate is the mean of four (E_q) values.

On the simultaneous coverage event, (L_q\le \mathrm{Var}(D_q)) and (U_q\ge(a_H-\theta_h)^2), so the frozen weight does not exceed the foldwise squared-error no-harm cap. This is a blockwise model-based certificate under patient independence within hospital. When every weight is zero, the four direct folds partition the audit and their mean equals the full direct audit exactly; the implementation records the numerical fallback residual.

The certificate is not claimed as a finite-population theorem for sampling without replacement, nor as a theorem for the pooled empirical reserve average.

## 8. Decision observability endpoints

The primary evidence object is hospital-by-budget state, not only a pooled metric.

- Absolute estimation error and MAE.
- CMDO regret = CMDO absolute error − direct absolute error.
- Correct resolution rate.
- False assurance rate: acceptable decision when the true hospital is unacceptable.
- False rejection rate: unacceptable decision when the true hospital is acceptable.
- Unresolved rate.
- Stable-decision cost: the smallest budget from which every later nested decision equals truth; otherwise 512 screened cases. ATC-style outcome-free estimates have cost zero when already stably correct.
- Hospital breadth: fraction of reserve hospitals with CMDO MAE ≤ direct MAE.
- Guard mechanism: Spearman association between absolute historical bias and mean CMDO transport weight.

## 9. Outcome-free matched-hospital witness

Before outcomes are opened, every reserve hospital is summarized by outcome-free score, confidence, age, sex, predicted-positive, ATC, and proxy telemetry. After standardization, the algorithm greedily selects ten disjoint nearest hospital pairs using Euclidean distance, with deterministic index tie-breaking. Outcomes then reveal each pair’s true fixed-threshold accuracy gap.

This test asks whether hospitals that look nearly interchangeable to outcome-free monitoring can nevertheless require different deployment decisions. The frozen conceptual-witness gate is a maximum paired true-accuracy gap of at least 0.03.

## 10. Frozen gates

### Integrity and certification

1. Twenty evaluable reserve hospitals.
2. Maximum exact-fallback residual <1×10⁻¹².
3. Zero covered-event certificate violations.
4. Mean simultaneous coverage ≥0.90.
5. Minimum hospital-budget simultaneous coverage ≥0.80.

### Empirical and decision safety

6. Pooled CMDO MAE ≤ direct MAE.
7. Worst hospital-budget CMDO regret ≤0.010.
8. Hospital noninferiority breadth ≥75%.
9. CMDO false assurance ≤ direct false assurance +0.005 at budget 256.

### Category-changing evidence

10. Stable-decision cost reduction ≥10%.
11. CMDO correct resolution at budget 256 ≥ direct.
12. Spearman correlation between absolute historical bias and transport weight ≤−0.50.
13. Maximum pre-outcome matched-pair true-accuracy gap ≥0.03.

Decision tiers are mechanically assigned from these groups. No gate is changed after reserve reveal.

## 11. One-time authorization and rerun policy

`PREPARE` freezes configuration, model assets, code hash, role table, target scores, telemetry, matched pairs, criteria, comparators, seeds, and vault hash. It then writes a pre-outcome seal and a non-authorizing review record.

`UNSEAL` requires an independently issued JSON containing the exact decision `AUTHORIZE_ONE_TIME_RESERVE_OUTCOME_ACCESS` and the matching seal, code, and vault hashes. After verification—but before reading the vault—it writes `StageU9_ONE_SHOT_ANALYSIS_STARTED_v1_0.json`. If that marker exists, rerun is prohibited even after an error. The work directory must instead be preserved for forensic review.

## 12. Outputs and sharing boundary

The authorized run writes replicate, state, hospital, method, decision, pair, and gate tables; publication figures; an Excel source-data workbook; a Markdown report; a complete-record JSON; and a SHA-256 manifest.

The canonical ZIP is built from an allowlist and rejects filenames associated with target scores, outcomes, restricted mappings, or row-level data. It contains code, protocol, authority records, aggregate outputs, figures, source data, and the manifest. The ZIP’s own hash is written to a companion commit JSON outside the ZIP.

## 13. Interpretation

U9 can support a claim that a prespecified guarded observer improved multicentre decision observability in this sealed reserve under the frozen operating point and criteria. It cannot establish causal benefit, prospective clinical utility, universal transportability, or independence of patients beyond the analysis model. APACHE IVa is used as an available locked deployment signal, not presented as a newly trained clinical model.
