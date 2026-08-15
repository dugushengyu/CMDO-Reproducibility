# CMDO reproducibility

This repository is the reviewer-facing reproducibility package for **Cross-Modal Diagnostic Observability (CMDO)**.

> **Current manuscript status (15 August 2026).** The independently validated seven-archive U4C–U7 baseline described below remains frozen and historically unchanged. The current manuscript additionally contains completed U8 and U9 Open Clinical operational extensions. Figure 5 is the integrated U6+U7 confirmation; Figure 6 combines U8 natural-prevalence confirmation with the completed U9 external-clinical boundary. See `docs/CURRENT_MANUSCRIPT_STATUS_2026-08-15.md` and `docs/audits/CMDO_U8_U9_Final_Integration_Audit_2026-08-15.md`. The earlier credentialed eICU pre-outcome branch is preserved separately as deferred independent confirmation and has not been overwritten.

The standard reviewer path is intentionally short: verify the package, run a small public-data end-to-end smoke test, install the seven byte-verified canonical result archives supplied with the submission, and regenerate the manuscript figures. U8/U9 Figure 6 uses the share-safe versioned source records under `source_data/figure6_u8_u9/`; no raw PhysioNet patient files are redistributed.

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

This is the fastest no-data integrity check. It verifies repository structure, source/provenance manifests, the reproduction DAG, adapters, cleanup commitments and unit tests.

### 3. Run the public end-to-end smoke test

```bash
python RUN_REVIEWER.py smoke --allow-network
```

This downloads a public UCI dataset, preprocesses it, fits a model, evaluates AUC and writes a ROC figure. It is an engineering smoke test, not a manuscript estimate.

### 4. Install the manuscript result assets

The submission includes one small binary companion ZIP, named for example:

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

```bash
python RUN_REVIEWER.py frozen
```

This byte-verifies all seven historical canonical result archives and regenerates the current main and Extended Data figures. U8/U9 operational Figure 6 is regenerated from the committed share-safe state/summary source records. It does **not** retrain the historical models or rerun the completed one-shot U9 analysis.

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

The machine-readable baseline record is `reviewer/VALIDATED_BASELINE.json`. U8 and the completed U9 Open Clinical branch are later versioned manuscript extensions and are not retrospectively inserted into that historical baseline.

## Scientific boundaries are disclosed, not hidden

CMDO distinguishes engineering reproducibility from scientific non-reproduction boundaries.

The current-runtime fresh chain reaches a disclosed T2-D scientific boundary rather than reproducing the historical 11/11 authorisation gate. Separately, downstream historical implementation has disclosed numerical-backend boundaries such as T2-MN. No threshold, gate, seed or budget is relaxed to turn those boundaries into a pass. The completed U9B external-system result likewise retains its prespecified partial verdict rather than tuning the observer after outcome access.

For reviewers who want the deeper history rather than the standard manuscript check:

```bash
python RUN_REVIEWER.py deep-plan
```

The detailed runner remains available as `RUN_REPRODUCTION.py`. Deep `full-claim` and `archival-continuation` modes are retrospective audit tools and are not required to reproduce the manuscript figures.

## Repository map

- `RUN_REVIEWER.py` — recommended reviewer entry point.
- `RUN_REPRODUCTION.py` — full reproduction runner and historical audit profiles.
- `provenance/` — dataset registry, canonical archive manifest, scientific boundaries and replay status.
- `scripts/` — package verification, asset installation/building and integrity utilities.
- `matlab/figures/` — manuscript figure generators.
- `source_data/figure6_u8_u9/` — share-safe U8/U9 data used by final Figure 6.
- `validation/u9_openclinical/v1_0/` — completed share-safe U9 Open Clinical records; no raw patient data.
- `legacy/original_authoritative/` — immutable historical source bytes; do not edit.
- `reviewer/VALIDATED_BASELINE.json` — compact sealed 14-August baseline status.
- `docs/REVIEWER_QUICKSTART.md` — detailed reviewer instructions and exit semantics.
- `docs/CURRENT_MANUSCRIPT_STATUS_2026-08-15.md` — current figure/evidence mapping.

## For maintainers: build the submission asset ZIP

When the seven exact canonical archives are present under `data/canonical_records/`:

```bash
python scripts/build_reviewer_asset_bundle.py
```

This writes `dist/CMDO-Reviewer-Assets-v1.0.zip` plus a SHA-256 sidecar. `dist/` and the canonical ZIPs remain Git-ignored; the binary bundle should be attached to the submission/release rather than committed into Git history.

## Governance

All default reviewer routes are retrospective. The earlier credentialed eICU U9 route remains excluded from the standard reviewer package and preserved as deferred confirmation. The completed open U9 branch is represented only by share-safe protocol/config/result/provenance records. No provider terms are accepted automatically, no restricted raw data are redistributed, and no new prospective-validation claim is created.
