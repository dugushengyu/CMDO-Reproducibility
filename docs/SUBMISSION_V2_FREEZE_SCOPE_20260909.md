# CMDO submission-v2 freeze scope — reviewer-slim v2.1.1

This candidate keeps the manuscript scientific architecture frozen while narrowing the reviewer acceptance path to the evidence actually used by the current submission.

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
- The eICU canonical shareable record remains immutable and restricted patient-level eICU/PhysioNet data are not redistributed.
- PPI++-style results remain a point-estimation comparator and do not redefine CMDO as an estimator-superiority claim.

## Reviewer acceptance scope

The reviewer-facing gate is:

```text
submission-v2 static scientific-integrity verification
-> current 5 main + 3 Extended Data displays
-> exactly 8 PNG + 8 PDF outputs
-> clean Git worktree
```

Historical developmental DAG replay, full-claim replay, archival continuation, network smoke, legacy Figure 5/6 rendering and the seven-canonical-archive asset bundle are not reviewer acceptance requirements.

They remain available only as maintainer/provenance material.

## Freeze procedure

The existing v2.1.0 freeze/tag is immutable and is not moved.

A v2.1.1 candidate may be merged/tagged only after:

1. the submission-v2 SHA-256 manifest verifies;
2. GitHub static integrity passes;
3. a fresh clone of the exact candidate commit passes `python RUN_REVIEWER.py all`;
4. the graphical run produces exactly eight PNG and eight PDF displays; and
5. the fresh-clone Git worktree remains clean.

Only the exact tested commit should receive the v2.1.1 submission tag.
