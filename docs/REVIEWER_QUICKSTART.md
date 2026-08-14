# Reviewer quickstart

The standard CMDO reviewer path has five steps. It is deliberately separated from the much deeper historical replay machinery.

## Step 1 — install the pinned Python environment

Reference Python version: **3.11**.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -c environment/replay-constraints.txt -r environment/requirements-replay.txt
```

Windows PowerShell activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

For CUDA-dependent deep replay, install the matching official PyTorch wheel first. CUDA is not required for the standard static or frozen-figure reviewer path.

## Step 2 — package acceptance

```bash
python RUN_REVIEWER.py check
```

Expected terminal message:

```text
=== CMDO REVIEWER ENGINEERING ACCEPTANCE PASS ===
```

This performs repository, source, provenance, DAG, adapter, cleanup-manifest and unit-test checks. It does not infer that every historical scientific authorisation gate reproduced.

## Step 3 — public-data end-to-end smoke test

```bash
python RUN_REVIEWER.py smoke --allow-network
```

Expected final profile state:

```text
CMDO profile smoke COMPLETE
```

The smoke route downloads public UCI-296 data, preprocesses it, fits a model, evaluates AUC and saves a ROC figure. It demonstrates that the download → preprocessing → model → evaluation → figure path works on the reviewer's machine. It is not a manuscript estimate.

## Step 4 — install the seven canonical manuscript archives

The submission should provide one binary companion ZIP, normally named:

```text
CMDO-Reviewer-Assets-v1.0.zip
```

Install it:

```bash
python RUN_REVIEWER.py install-assets --bundle /path/to/CMDO-Reviewer-Assets-v1.0.zip
```

Windows example:

```powershell
python .\RUN_REVIEWER.py install-assets --bundle "$HOME\Downloads\CMDO-Reviewer-Assets-v1.0.zip"
```

The installer searches the supplied bundle for the seven filenames declared in `provenance/canonical_archives_manifest.csv`. Every archive must match the frozen byte size and SHA-256 exactly, and its internal ZIP CRC must pass. Only then is it materialized under `data/canonical_records/`.

The reviewer's machine does **not** need the historical Google Drive directory tree.

## Step 5 — regenerate manuscript figures

MATLAB must be callable as `matlab`. The reference reviewer run used MATLAB R2024b with the Statistics and Machine Learning Toolbox.

```bash
python RUN_REVIEWER.py frozen
```

Expected final profile state:

```text
CMDO profile frozen COMPLETE
```

This route:

1. rechecks repository/source/provenance integrity;
2. byte-verifies all seven canonical result archives;
3. regenerates the current manuscript main and Extended Data figures from those records.

It does not retrain the historical models.

## One-command standard route

After installing the asset ZIP:

```bash
python RUN_REVIEWER.py all --allow-network
```

The command runs `check`, `smoke`, canonical verification and `frozen` in sequence.

Use a different run prefix if you want to keep several independent reviewer runs:

```bash
python RUN_REVIEWER.py all --allow-network --run-prefix REVIEWER-RUN2
```

Generated outputs are written under `outputs/reviewer/` unless `--output-root` is supplied.

## Validated baseline

The scientific baseline at commit `57962f57ef11902bd9fa437412514d994d3af864` was independently exercised twice on 14 August 2026. The sealed local reviewer audit reported:

- public smoke: PASS x2;
- canonical archive identity: 7/7 exact;
- canonical-to-publication-figure route: PASS x2;
- exact-first cross-run comparison: PASS;
- numerical-boundary registry: PASS;
- threshold relaxation: none;
- U9/eICU included: false;
- Stage12 authorised: false.

See `reviewer/VALIDATED_BASELINE.json` for the machine-readable record.

## Deep replay is optional and deliberately separate

A reviewer who wants to inspect the deeper historical DAG can first print both plans:

```bash
python RUN_REVIEWER.py deep-plan
```

The underlying full runner is:

```bash
python RUN_REPRODUCTION.py <profile> [options]
```

Available deep profiles include `full-claim` and `archival-continuation`.

### Fresh full-claim boundary

The current-runtime fresh path reaches a disclosed T2-D scientific non-reproduction boundary: the stage executes, but the historical 11/11 authorisation gate is not reproduced. The runner records `SCIENTIFIC_DIVERGENCE_BOUNDARY`, returns exit code **4**, and does not represent downstream stages as a fresh accepted chain. No gate threshold is relaxed.

### Archival continuation

`archival-continuation` starts from byte-verified accepted historical parents and audits downstream historical implementation. It is explicitly retrospective and must not be described as a fresh raw-to-science reproduction.

U9/eICU is excluded from all default reviewer profiles.

## Exit codes

- `0` — selected profile completed.
- `1` — engineering/integrity/stage execution failure.
- `3` — explicit prerequisite block, such as missing assets/runtime/network acknowledgement.
- `4` — sealed `SCIENTIFIC_DIVERGENCE_BOUNDARY`; scientific execution occurred but a frozen authorisation boundary was not reproduced.

## Maintainer-only asset packaging

With the seven exact canonical archives present under `data/canonical_records/`:

```bash
python scripts/build_reviewer_asset_bundle.py
```

The script produces `dist/CMDO-Reviewer-Assets-v1.0.zip` and a SHA-256 sidecar. The output is for the submission/release attachment, not for Git history.
