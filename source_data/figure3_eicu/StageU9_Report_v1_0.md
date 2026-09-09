# CMDO U9 sealed multicentre decision-observability report

**Frozen protocol:** SEALED_MULTICENTRE_DECISION_OBSERVABILITY_RESERVE (v1.0)

**Canonical decision:** `INTEGRITY_SUPPORTED_EMPIRICAL_SAFETY_NOT_CONFIRMED`

## Primary reserve summary

- Evaluable reserve hospitals: 20 of 20.
- Pooled direct MAE: 0.027772.
- Pooled CMDO MAE: 0.026762.
- Relative CMDO MAE gain: 3.64%.
- Stable-decision cost reduction: -0.83%.
- Maximum hospital-budget CMDO regret: 0.001539.
- Hospital noninferiority breadth: 70.0%.
- Mean/minimum simultaneous coverage: 0.981 / 0.945.
- Covered-event certificate violations: 0.
- Maximum direct-fallback residual: 0.
- Maximum outcome-free matched-pair accuracy gap after reveal: 0.0805.

## Method comparison

| Method | MAE | RMSE | Bias | Correct resolution | False assurance | Unresolved |
|---|---:|---:|---:|---:|---:|---:|
| DIRECT | 0.027772 | 0.037040 | 0.000176 | 0.839 | 0.117 | 0.085 |
| STATIC | 0.025289 | 0.033213 | -0.004642 | 0.838 | 0.117 | 0.089 |
| ATC | 0.035880 | 0.047423 | 0.001107 | 0.800 | 0.667 | 0.050 |
| PPI_PLUS_PLUS_STYLE | 0.016252 | 0.021818 | -0.000082 | 0.870 | 0.079 | 0.088 |
| CMDO | 0.026762 | 0.035653 | -0.001200 | 0.838 | 0.117 | 0.088 |

## Decision summary by screened-case budget

| Method | Budget | Correct resolution | False assurance | False rejection | Unresolved | Stable cost |
|---|---:|---:|---:|---:|---:|---:|
| DIRECT | 64 | 0.805 | 0.148 | 0.091 | 0.096 | 138.0 |
| DIRECT | 128 | 0.843 | 0.112 | 0.071 | 0.080 | 138.0 |
| DIRECT | 256 | 0.870 | 0.092 | 0.044 | 0.079 | 138.0 |
| STATIC | 64 | 0.805 | 0.148 | 0.091 | 0.096 | 139.2 |
| STATIC | 128 | 0.843 | 0.112 | 0.071 | 0.080 | 139.2 |
| STATIC | 256 | 0.866 | 0.092 | 0.034 | 0.091 | 139.2 |
| ATC | 64 | 0.800 | 0.667 | 0.059 | 0.050 | 102.4 |
| ATC | 128 | 0.800 | 0.667 | 0.059 | 0.050 | 102.4 |
| ATC | 256 | 0.800 | 0.667 | 0.059 | 0.050 | 102.4 |
| PPI_PLUS_PLUS_STYLE | 64 | 0.856 | 0.128 | 0.059 | 0.074 | 126.9 |
| PPI_PLUS_PLUS_STYLE | 128 | 0.870 | 0.065 | 0.034 | 0.091 | 126.9 |
| PPI_PLUS_PLUS_STYLE | 256 | 0.886 | 0.045 | 0.012 | 0.097 | 126.9 |
| CMDO | 64 | 0.805 | 0.148 | 0.092 | 0.094 | 139.2 |
| CMDO | 128 | 0.843 | 0.112 | 0.071 | 0.080 | 139.2 |
| CMDO | 256 | 0.866 | 0.092 | 0.036 | 0.089 | 139.2 |

## Frozen gate table

| Gate | Category | Threshold | Observed | Result |
|---|---|---|---:|---|
| twenty_independent_reserve_hospitals | integrity | >=20 | 20 | PASS |
| exact_full_direct_fallback | integrity | <1e-12 | 0 | PASS |
| covered_event_certificate_violations | certification | =0 | 0 | PASS |
| mean_simultaneous_coverage | certification | >=0.90 | 0.981167 | PASS |
| minimum_state_simultaneous_coverage | certification | >=0.80 | 0.945 | PASS |
| pooled_cmdo_mae_noninferiority | empirical_safety | CMDO<=Direct | -0.00101005 | PASS |
| worst_hospital_budget_regret | empirical_safety | <=0.010 | 0.0015393 | PASS |
| hospital_breadth | empirical_safety | >=75% | 0.7 | FAIL |
| false_assurance_noninferiority | decision_safety | CMDO<=Direct+0.005 | 0 | PASS |
| stable_decision_cost_reduction | decision_efficiency | >=10% | -0.00834492 | FAIL |
| max_budget_correct_resolution_noninferiority | decision_efficiency | CMDO>=Direct | -0.0035 | FAIL |
| bias_guard_mechanism | mechanism | Spearman<=-0.50 | -0.894737 | PASS |
| matched_telemetry_witness | conceptual_witness | max accuracy gap>=0.03 | 0.0805285 | PASS |

## Matched-hospital witness

10 hospital pairs were selected before reserve outcomes were opened using outcome-free telemetry only.
After reveal, the median and maximum absolute true-accuracy gaps were 0.0179 and 0.0805.

## Interpretation boundary

Hospitals are deidentified deployment units in a retrospective database. The blockwise certificate is interpreted under the prespecified patient-independence superpopulation model. Aggregate MAE, decision efficiency and matched-pair contrasts are empirical reserve results, not a universal no-harm theorem.

No row-level eICU record, target-score file, outcome vault, raw hospital identifier or patient identifier is included in the canonical shareable ZIP.
