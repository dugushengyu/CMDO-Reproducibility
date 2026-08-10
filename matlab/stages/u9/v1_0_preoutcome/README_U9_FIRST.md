# CMDO U9 — run this package in two phases

U9 is a sealed, hospital-independent external-reserve test using the eICU Collaborative Research Database v2.0. It evaluates whether CMDO improves the observability of a fixed clinical-deployment decision across 20 real hospital units while retaining an exact direct-estimator fallback.

## What you need

- MATLAB R2022b or newer.
- Statistics and Machine Learning Toolbox.
- Credentialed local access to eICU-CRD v2.0 under the PhysioNet data-use agreement.
- These official tables, either as `.csv` or `.csv.gz`: `patient`, `apachePatientResult`, and `hospital`.
- Enough free disk space for the official tables, a decompression cache, and U9 outputs.

The package contains no eICU patient data. Do not upload or return any file from `00_RESTRICTED_DO_NOT_SHARE`.

## Exact run order

1. Open MATLAB in this package folder and run `RUN_SELFTEST.m`.
2. Set `CMDO_EICU_ROOT`, or edit the one path in `RUN_DATA_ADAPTER.m`; then run it.
3. Run `RUN_PREPARE.m`.
4. Stop. Return only the six share-safe files listed in `U9_Results_Return_Checklist_v1_0.md`.
5. After an independent reviewer issues a hash-matched authorization JSON, place it exactly where the checklist says.
6. Run `RUN_UNSEAL.m` once.
7. Return `CMDO_U9_Canonical_Shareable_Record_v1_0.zip` and `StageU9_Canonical_Zip_Commit_v1_0.json`.

## Why this is not one unsealed script

The official APACHE result table stores the model score and hospital-mortality outcome together. `ADAPT` therefore performs a one-time physical split: outcome-free roster, development outcomes, and a reserve-outcome vault. `PREPARE` reads the first two only; it hashes the reserve vault as bytes and freezes the code, criteria, seeds, scores, comparators, telemetry pairs, and gates. `UNSEAL` refuses to run unless every current hash matches both the pre-outcome seal and an independently issued authorization.

## Primary frozen estimand and decision

- Unit: one eligible eICU hospital.
- Model signal: APACHE IVa predicted hospital-mortality score.
- Outcome: actual hospital mortality.
- Metric: natural-prevalence accuracy at a threshold selected in source hospitals only.
- Acceptance criterion: hospital accuracy at least the median accuracy of historical hospitals.
- Decision outputs: acceptable, unacceptable, or unresolved within a ±0.01 guard band.
- Audit budgets: 64, 128, and 256 screened cases; 200 frozen replicates per reserve hospital.

Full details and claim boundaries are in `StageU9_Protocol_v1_0.docx` and `.md`.

## Expected stopping points

- After `ADAPT`: the command window says no reserve statistic was computed or printed.
- After `PREPARE`: the command window prints a pre-outcome seal hash and says **DO NOT RUN UNSEAL**.
- After authorized `UNSEAL`: MATLAB writes figures, tables, source data, a full gate report, a manifest, the canonical shareable ZIP, and a companion SHA-256 commit.

If MATLAB errors before writing `StageU9_ONE_SHOT_ANALYSIS_STARTED_v1_0.json`, correct the stated pre-unseal issue and rerun. If that marker exists, do not rerun or delete it; preserve the entire work directory and return the error plus logs for forensic review.
