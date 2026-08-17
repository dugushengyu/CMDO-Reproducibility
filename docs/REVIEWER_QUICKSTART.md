# Reviewer quickstart

The standard CMDO reviewer path is deliberately separated from the deeper historical replay machinery. The default route verifies the repository, audits the final sealed Figure 5/6 records, exercises a public-data smoke path, byte-verifies the canonical manuscript assets, and regenerates the manuscript figures.

## Step 1 — install the pinned standard reviewer environment

Reference Python version: **3.11**.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -c environment/replay-constraints.txt -r environment/requirements-reviewer.txt
```

Windows PowerShell activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

`environment/requirements-reviewer.txt` is intentionally minimal. It contains the numerical/model/plotting dependencies used by the standard reviewer path and omits Jupyter/JupyterLab, PyTorch and deep-replay data tooling.

Only reviewers who choose to execute the optional historical/deep replay profiles need the larger environment:

```bash
python -m pip install -c environment/replay-constraints.txt -r environment/requirements-replay.txt
```

For CUDA-dependent deep replay, install the matching official PyTorch wheel first. CUDA is not required for the standard static or frozen-figure reviewer path.

## Step 2 — package acceptance and final Figure 5/6 audit

```bash
python RUN_REVIEWER.py check
```

Expected terminal messages include:

```text
=== CMDO FINAL FIGURE 5/6 AUDIT PASS ===
=== CMDO REVIEWER ENGINEERING ACCEPTANCE PASS ===
```

This performs repository, source, provenance, DAG, final Figure 5/6 and unit-test checks. It does not infer that every historical scientific authorisation gate reproduced.

The Figure 5/6 audit can also be run directly:

```bash
python scripts/audit_final_figure56.py
```

The final Figure 5 and Figure 6 MATLAB files are sealed renderers: the frozen derived values required for rendering are embedded in the scripts, so they do not read scientific inputs from `Downloads`, Google Drive, a manuscript working directory, or another machine-specific data path at runtime. Independent audit companions remain tracked under `source_data/` so the embedded values can be checked against repository records.

### Fastest Figure 5/6-only reproduction

If the reviewer only wants to reproduce the two new final manuscript figures, no canonical asset ZIP is required. With MATLAB callable as `matlab`, run:

```bash
python RUN_REVIEWER.py figures56
```

This command first runs the sealed Figure 5/6 audit, then renders only `Figure5()` and `Figure6()` into `outputs/reviewer/figures/main/`. It does not run the older canonical-archive figure pipeline and does not touch deferred eICU data.

## Step 3 — public-data end-to-end smoke test

```bash
python RUN_REVIEWER.py smoke --allow-network
```

Expected final profile state:

```text
CMDO profile smoke COMPLETE
```

The smoke route downloads public UCI-296 data, preprocesses it, fits a model, evaluates AUC and saves a ROC figure. Its Python imports are limited to the standard reviewer numerical stack (`pandas`, `matplotlib`, `scikit-learn` plus their NumPy/SciPy dependencies). It demonstrates that the download → preprocessing → model → evaluation → figure path works on the reviewer's machine. It is not a manuscript estimate.

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

MATLAB must be callable as `matlab`. The reference reviewer environment uses MATLAB R2024b with the Statistics and Machine Learning Toolbox.

```bash
python RUN_REVIEWER.py frozen
```

Expected final profile state:

```text
CMDO profile frozen COMPLETE
```

Before MATLAB rendering, this command reruns the final Figure 5/6 static audit. The frozen route then:

1. rechecks repository/source/provenance integrity;
2. byte-verifies the seven canonical result archives used by the earlier manuscript figure pipeline;
3. regenerates the current main and Extended Data figures;
4. runs the current `Figure5()` and `Figure6()` sealed renderers into the same reviewer `figures/main` output tree as Figure 4;
5. builds compatibility PDFs and writes the figure-run report.

The final Figure 5/6 sealed-render path reproduces the manuscript figures from frozen derived records. This is intentionally distinguished from a fresh raw-to-science replay of restricted/deferred U9 data.

## One-command standard route

After installing the asset ZIP:

```bash
python RUN_REVIEWER.py all --allow-network
```

The command runs static acceptance (including the Figure 5/6 audit), public smoke, canonical verification and frozen figure regeneration in sequence.

Use a different run prefix if you want to keep several independent reviewer runs:

```bash
python RUN_REVIEWER.py all --allow-network --run-prefix REVIEWER-RUN2
```

Generated outputs are written under `outputs/reviewer/` unless `--output-root` is supplied.

## Figure 5/6 provenance notes

- `source_data/figure6_u8_u9/` retains the share-safe U8/U9A/U9B state and summary records audited against the final Figure 5 embedded values. The directory name is historical; these records now support current manuscript Figure 5.
- `source_data/figure6_admissibility/CMDO_Admissibility_State_MSE_Audit.csv` retains the six exact columns consumed by Figure 6 for all 185 states. The originating full 26-column table has SHA-256 `a0ad0c9f9feded26b9b32f732ae62d7639d5ff91be983cb54a04525b0efc6d03`; the Git-tracked audit extract has SHA-256 `4ef09304a0dbb4110130b9543b05bd8a7d0f34f22dd0ecef1cb6ef758c6174c4`.
- `source_data/figure6_admissibility/` also retains the U9B composability decomposition and strict-split mechanistic-control tables used to audit Figure 6 panels c/d.
- `provenance/final_figure56_seal.json` records the final renderer hashes and expected scientific invariants.
- `docs/FIGURE5_6_REPRODUCIBILITY_AUDIT_2026-08-17.md` gives the detailed scope and interpretation boundary.

## Validated baseline and current update

The deeper scientific baseline at commit `57962f57ef11902bd9fa437412514d994d3af864` was independently exercised twice on 14 August 2026. The sealed local reviewer audit reported public smoke PASS x2, 7/7 canonical archive identity, canonical-to-publication-figure PASS x2, exact-first cross-run comparison PASS, and no threshold relaxation.

The 17 August Figure 5/6 update adds the final sealed renderers and static audit described above. It does **not** rewrite the historical baseline or silently claim a new independent raw-to-science U9 replay. Maintainers should run `RUN_REVIEWER.py check`, `RUN_REVIEWER.py figures56`, and, when the canonical asset ZIP is installed, `RUN_REVIEWER.py frozen` after pulling this update to record the new local renderer acceptance.

See `reviewer/VALIDATED_BASELINE.json` for the historical machine-readable baseline.

## Deep replay is optional and deliberately separate

A reviewer who wants to inspect the deeper historical DAG can first print both plans without installing the deep replay environment:

```bash
python RUN_REVIEWER.py deep-plan
```

The underlying full runner is:

```bash
python RUN_REPRODUCTION.py <profile> [options]
```

Available deep profiles include `full-claim` and `archival-continuation`. Actual execution of those profiles uses `environment/requirements-replay.txt` rather than the minimal reviewer requirements.

### Fresh full-claim boundary

The current-runtime fresh path reaches a disclosed T2-D scientific non-reproduction boundary: the stage executes, but the historical 11/11 authorisation gate is not reproduced. The runner records `SCIENTIFIC_DIVERGENCE_BOUNDARY`, returns exit code **4**, and does not represent downstream stages as a fresh accepted chain. No gate threshold is relaxed.

### Archival continuation

`archival-continuation` starts from byte-verified accepted historical parents and audits downstream historical implementation. It is explicitly retrospective and must not be described as a fresh raw-to-science reproduction.

The deferred eICU branch is excluded from all default reviewer profiles.

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
