# CMDO submission v2 freeze scope — 2026-09-09

This branch synchronizes the reproducibility repository with the manuscript architecture frozen on 9 September 2026.

## Scientific architecture

`IDENTIFY -> REUSE -> CERTIFY -> PRESERVE`

Submission displays:
1. Figure 1 — evidential order and information roles.
2. Figure 2 — IDENTIFY: outcome-free non-identifiability and outcome restoration.
3. Figure 3 — REUSE: frozen confirmation, mismatch sensing, 185-state post-completion geometry, and the deferred sealed 20-hospital eICU replication.
4. Figure 4 — CERTIFY: PCC robust-safe boundary, exact finite-sample certification, information-cost scaling and retrospective 185-state projection.
5. Figure 5 — PRESERVE: fixed-use versus adaptive risk and the adaptation frontier.
6. Extended Data Figure 1 — developmental outcome-free falsification.
7. Extended Data Figure 2 — role separation and locked mechanism challenge.
8. Extended Data Figure 3 — controlled historical-misspecification robustness-efficiency operating region.

## Frozen scientific constraints

- The 185-state synthesis remains exactly `80 U6 + 80 U7 + 12 U8 + 9 U9A + 4 U9B = 185`.
- Deferred eICU is reported separately and is not retroactively added to the 185-state synthesis or PCC projection.
- U10's prospective mechanism verdict remains `MECHANISM_NOT_CONFIRMED`; post-completion localization does not overwrite it.
- The eICU canonical shareable ZIP remains immutable and is not rebuilt by this repository update.
- No raw credentialed eICU/PhysioNet patient-level data are added to Git.
- PPI++-style results are retained as a point-estimation comparator and do not redefine CMDO as an estimator-superiority claim.

## Freeze procedure

This branch is not a final submission tag until all current renderer/source changes are complete, a v2 SHA-256 manifest is committed, and a fresh clone of the exact candidate commit passes the v2 acceptance gate on the author workstation. Only that exact tested commit may be moved to `main` and tagged `cmdo-submission-v2.0.0`.
