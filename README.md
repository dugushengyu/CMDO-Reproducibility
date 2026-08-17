# CMDO reproducibility

This repository is the reviewer-facing reproducibility package for **Cross-Modal Diagnostic Observability (CMDO)**.

> **Current manuscript status (17 August 2026).** The independently validated seven-archive U4C–U7 baseline remains frozen and historically unchanged. The current manuscript additionally contains completed U8 and U9 Open Clinical operational extensions plus the final evidence-admissibility synthesis. Figure 5 reports the U8 temporal natural-prevalence confirmation together with the U9A/U9B external-system operational boundary. Figure 6 synthesizes all 185 frozen U6/U7/U8/U9A/U9B states under the evidence-admissibility law and includes the U9B strict-split mechanistic control. The earlier credentialed eICU pre-outcome branch is preserved separately as deferred independent confirmation and has not been overwritten.

The standard reviewer path is intentionally short: verify the package, run a small public-data end-to-end smoke test, install the seven byte-verified canonical result archives supplied with the submission, and regenerate the manuscript figures. Final Figure 5 and Figure 6 are sealed renderers whose required frozen derived values are embedded in the MATLAB scripts and independently audited against tracked share-safe records under `source_data/`. No raw PhysioNet patient files are redistributed.

## Start here

### 1. Create the Python environment

Python 3.11 is the reference replay version.

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the pinned replay environment:

```bash
python -m pip install -c environment/replay-constraints.txt -r environment/requirements-replay.txt
```

### 2. Verify the repository

```bash
python RUN_REVIEWER.py check
```

This is the fastest no-data integrity check. It verifies repository structure, source/provenance manifests, the reproduction DAG, final Figure 5/6 audit records, adapters and unit tests.

### 3. Run the public end-to-end smoke test

```bash
python RUN_REVIEWER.py smoke --allow-network
```

This downloads a public UCI dataset, preprocesses it, fits a model, evaluates AUC and writes a ROC figure. It is an engineering smoke test, not a manuscript estimate.

### 4. Install the manuscript result assets

The submission includes one binary companion ZIP:

```text
CMDO-Reviewer-Assets-v1.0.zip
```

Install it with:

```bash
python RUN_REVIEWER.py install-assets --bundle /path/to/CMDO-Reviewer-Assets-v1.0.zip
```

The installer accepts the seven canonical archives only when their filename, byte size, SHA-256 and inner ZIP CRC match `provenance/canonical_archives_manifest.csv` exactly. The historical Google Drive working tree is not required.

### 5. Regenerate the manuscript figures

MATLAB R2024b or a compatible MATLAB installation must be callable as `matlab`; the Statistics and Machine Learning Toolbox is required.

For the two final sealed figures only:

```bash
python RUN_REVIEWER.py figures56
```

For the complete frozen manuscript-figure route after installing the asset ZIP:

```bash
python RUN_REVIEWER.py frozen
```

The frozen route byte-verifies all seven historical canonical result archives and regenerates the current main and Extended Data figures, then renders the final sealed Figure 5/6 into the same reviewer output tree. It does **not** retrain the historical models or rerun the completed one-shot U9 analysis.

### One-command standard reviewer route

After the asset ZIP is installed:

```bash
python RUN_REVIEWER.py all --allow-network
```

That runs package acceptance, the public-data smoke test, canonical verification and frozen manuscript-figure reproduction in sequence.

## What was independently validated

The scientific baseline at commit `57962f57ef11902bd9fa437412514d994d3af864` was independently run twice and sealed on 14 August 2026:

- public end-to-end smoke: **PASS x2**;
- seven canonical archives: **7/7 byte exact**;
- canonical records to publication figures: **PASS x2**;
- cross-run comparison: **exact-first PASS**;
- disclosed numerical-boundary registry: **PASS**;
- threshold relaxation: **none**;
- U9/eICU: **not included in that 14-August baseline**;
- Stage12 authorisation: **false**.

The machine-readable baseline record is `reviewer/VALIDATED_BASELINE.json`. U8, U9 Open Clinical and the final Figure 5/6 synthesis are later versioned manuscript extensions and are not retrospectively inserted into that historical baseline.

## Scientific boundaries are disclosed, not hidden

CMDO distinguishes engineering reproducibility from scientific non-reproduction boundaries.

The current-runtime fresh chain reaches a disclosed T2-D scientific boundary rather than reproducing the historical 11/11 authorisation gate. Separately, downstream historical implementation has disclosed numerical-backend boundaries such as T2-MN. No threshold, gate, seed or budget is relaxed to turn those boundaries into a pass. The completed U9B external-system result likewise retains its prespecified partial verdict rather than tuning the observer after outcome access. The strict-split U9B analysis is explicitly post-hoc mechanistic evidence and does not change that frozen verdict.

For reviewers who want the deeper history rather than the standard manuscript check:

```bash
python RUN_REVIEWER.py deep-plan
```

The detailed runner remains available as `RUN_REPRODUCTION.py`. Deep `full-claim` and `archival-continuation` modes are retrospective audit tools and are not required to reproduce the manuscript figures.

## Repository map

- `RUN_REVIEWER.py` — recommended reviewer entry point.
- `RUN_CLEANROOM_REVIEWER.ps1` — maintainer-only final submission build plus stranger-style clean-room acceptance.
- `RUN_REPRODUCTION.py` — full reproduction runner and historical audit profiles.
- `provenance/` — dataset registry, canonical archive manifest, final Figure 5/6 seal, scientific boundaries and replay status.
- `scripts/` — package verification, asset installation/building, clean-room acceptance and integrity utilities.
- `matlab/figures/` — manuscript figure generators.
- `source_data/figure6_u8_u9/` — historical directory name retaining share-safe U8/U9 records audited against current Figure 5.
- `source_data/figure6_admissibility/` — 185-state evidence-admissibility and U9B mechanism records audited against current Figure 6.
- `validation/u9_openclinical/v1_0/` — completed share-safe U9 Open Clinical records; no raw patient data.
- `legacy/original_authoritative/` — immutable historical source bytes; do not edit.
- `reviewer/VALIDATED_BASELINE.json` — compact sealed 14-August baseline status.
- `docs/REVIEWER_QUICKSTART.md` — detailed reviewer instructions and exit semantics.
- `docs/CLEANROOM_REVIEWER_ACCEPTANCE.md` — final maintainer clean-room acceptance protocol.

## For maintainers: final submission candidate

With the seven exact canonical archives present under `data/canonical_records/`, the final maintainer command on Windows is:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_CLEANROOM_REVIEWER.ps1
```

It builds and hashes both reviewer delivery artifacts, performs a fresh clone at the exact Git commit, creates a new Python 3.11 environment, installs the exact canonical asset ZIP, reruns the reviewer acceptance, regenerates Figure 5/6, executes the public smoke route, runs the frozen figure path and requires the fresh clone to remain Git-clean.

The submission build writes under `dist/`:

- `CMDO-Reviewer-Assets-v1.0.zip` plus SHA-256 sidecar;
- `CMDO-Reproducibility-Reviewer-Portable-v1.0.zip` plus SHA-256 sidecar;
- `CMDO-Submission-Candidate-v1.0_MANIFEST.json`;
- `CMDO-Submission-Candidate-v1.0_SHA256.txt`.

`dist/` and the canonical ZIPs remain Git-ignored. Binary reviewer bundles belong in the submission/release attachment, not in Git history.

## Governance

All default reviewer routes are retrospective. The earlier credentialed eICU U9 route remains excluded from the standard reviewer package and preserved as deferred confirmation. The completed open U9 branch is represented only by share-safe protocol/config/result/provenance records. No provider terms are accepted automatically, no restricted raw data are redistributed, and no new prospective-validation claim is created.
