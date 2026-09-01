# CMDO reproducibility

This repository contains the reviewer-facing reproducibility record for the final CMDO manuscript.

## Final scientific architecture

The manuscript is organized as **IDENTIFY -> REUSE -> PRESERVE**.

Current submission figure roles are:

- Figure 1 — evidential order and system structure
- Figure 2 — IDENTIFY: same monitored evidence, opposite compatible performance, and outcome-audit contraction
- Figure 3 — REUSE: historical-evidence value and the fixed-use admissibility boundary
- Figure 4 — PRESERVE: adaptation cost and the adaptation frontier
- Figure 5 — controlled operating-region comparison under dense historical misspecification
- Extended Data Figure 1 — developmental falsification of a universal outcome-free route
- Extended Data Figure 2 — role-separation and coupling-pathway diagnostics

## Exact submitted figures

From a fresh Git clone, open MATLAB at repository root and run:

```matlab
RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)
```

This is the manuscript-defining route. It reads only tracked repository-relative frozen derived records and renders Figure 1-5 plus Extended Data Figures 1-2. It does not use an author-machine repository/data path and does not require network access during rendering.

## One-command reviewer end-to-end audit

For a broader machine-portability check, run:

```matlab
RUN_REVIEWER_E2E
```

The command uses an isolated Python environment under the operating-system temporary directory and performs, in order:

1. repository-relative input/path isolation checks;
2. the existing reviewer engineering acceptance checks;
3. a genuine public UCI-296 download -> preprocessing -> model fitting -> AUC -> ROC-figure smoke loop;
4. the reconstructed dense-Lambda stress replay as a diagnostic only;
5. the exact seven submitted figures from tracked frozen submission records; and
6. a historical raw-to-science plan plus a final Git-clean audit.

For an offline exact-figure/path-isolation check:

```matlab
RUN_REVIEWER_E2E('Offline',true)
```

A GitHub Actions matrix also runs the standard-library submission portability audit on Windows, macOS and Linux:

```bash
python scripts/verify_submission_portability.py
```

## Figure 5 source roles

The manuscript Figure 5 is rendered from the tracked frozen state-summary CSV:

```text
source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv
```

The exact frozen fingerprint is checked before rendering, including the critical tested Lambda matrix, the shared-robust-region mean CMDO minus U-stat advantage of 1.0817 percentage points, and the 80% paired-state win fraction.

The reconstructed dense-Lambda generator under:

```text
scripts/stress_replay/
```

is a post-completion implementation diagnostic. The original local generator was lost and the reconstructed program is **not** claimed to reproduce the original random-number trajectory byte-for-byte. It never overwrites or defines the manuscript Figure 5.

## Figure 1 frozen asset

Figure 1 is rendered from:

```text
source_data/figure1_assets/Figure1_assets_selected_v1.mat
```

SHA-256:

```text
30490a2586a9394fad868159ccd1f0248b0d9afc17d9bc970456c425c63925e7
```

The reviewer-facing frozen-input manifest is:

```text
provenance/submission_github_native_v4_manifest.csv
```

## Reproducibility boundary

There are three deliberately separate claims:

- **Exact submission reproduction:** tracked frozen derived records -> exact final manuscript figures. This is the primary reviewer pathway.
- **Public raw-data engineering smoke:** public data -> preprocess -> train -> evaluate -> smoke figure. This validates cross-machine execution but is not a manuscript estimate.
- **Historical raw-to-science replay:** a much deeper retrospective reconstruction retained for provenance. It can require network/provider availability, GPU acceleration, manual or credentialed assets, and hours to days of runtime. It also contains a disclosed scientific-divergence boundary, so it is not a prerequisite for reproducing the submitted figures.

Restricted patient-level records are not redistributed, and no raw PhysioNet patient waveforms are required by the exact submission-figure route.

## Portability

The reviewer route is designed for Windows, macOS and Linux with Git, Python 3.10+ and MATLAB. Exact pixel hashes are not required across operating systems because fonts, PDF backends and rasterization can differ; acceptance is based on numerical fingerprints, successful renderer audits and the presence of all expected PNG/PDF outputs.

## Freeze policy

- Frozen protocols and locked prospective verdicts must not be overwritten.
- Post-completion analyses remain explicitly labelled as such.
- The final Figure 5 uses the tracked frozen state-summary CSV, not reconstructed stress output.
- An immutable submission release/tag should be cut only after a fresh-clone `RUN_REVIEWER_E2E` acceptance pass.
