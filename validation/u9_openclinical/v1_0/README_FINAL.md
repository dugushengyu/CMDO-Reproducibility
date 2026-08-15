# U9 Open Clinical v1.0 — completed result

This directory is the share-safe repository record for the completed manuscript-facing U9 Open Clinical programme.

- **U9A:** UCI Heart Disease multicentre bridge/falsification test.
- **U9B:** PhysioNet Challenge 2019 System-A-to-System-B primary external-system reserve.
- **eICU:** the earlier credentialed pre-outcome branch under `matlab/stages/u9/v1_0_preoutcome/` is preserved separately as deferred independent confirmation.

Frozen decisions:

- U9A: `BRIDGE_FALSIFICATION_SIGNAL`.
- U9B: `PARTIAL_EXTERNAL_CERTIFICATION_EFFICIENCY_NOT_CONFIRMED`.

U9B passed the prespecified sample-count, exact-fallback, zero-certificate-violation, coverage, root-budget-slope, worst-budget-regret and nontrivial-borrowing gates. Pooled observer MAE was nevertheless higher than same-budget direct MAE, so pooled noninferiority failed and the partial verdict is retained.

`PACKAGE_SHA256_v1_0.csv` and `StageU9_OpenClinical_PreOutcome_Seal_v1_0.json` record the identity of the original sealed pre-outcome package. This repository directory is a share-safe audit mirror: it contains the scientific protocol/configuration/code and completed result/provenance records needed to understand the manuscript result, but it is not intended to reproduce every convenience launcher from the original local sealed ZIP. The authoritative completed binary identity remains the final U9 canonical ZIP SHA-256 `32e05cd2b507bfa839257a49e9b307dce4c3529180c02c3717c182538c0e4e54`; the replicate-level share-safe forensic export SHA-256 is `c2e1c59c8378be842a4398eb227c3d250ef0e21e176922bfeb446682ce640919`.

No raw patient-level PhysioNet PSV files are redistributed here.
