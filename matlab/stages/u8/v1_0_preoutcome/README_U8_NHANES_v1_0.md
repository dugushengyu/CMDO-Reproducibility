# CMDO U8 MATLAB package

Package patch release: **v1.0.1**. The scientific protocol remains v1.0.
This patch corrects only the MATLAB preflight check: `predict` is invoked as
a fitted-model method and must not be tested as a standalone path function.
No model, data, estimand, seed, budget, gate or outcome-handling logic changed.

This package implements a new evidence branch for the current CMDO observability manuscript. It does **not** reopen, repurpose or modify the legacy DDO-2 Stage 12 or any old locked-blind asset.

## Scientific role

U8 asks whether a theorem-aligned observer can operate under a realistic screened-case budget rather than a post hoc balanced positive/negative budget.

- Source model: NHANES 2011–2012.
- Transparent historical-performance cycle: NHANES 2013–2014.
- One-time temporal reserves: NHANES 2015–2016, 2017–2018 and August 2021–August 2023.
- Outcome: elevated glycohaemoglobin, HbA1c ≥ 5.7%.
- Primary performance criterion: accuracy at a source-frozen threshold.
- Primary audit: simple random cases at natural prevalence, with screened-case budgets 128, 256, 512 and 1,024.
- Observer: four-fold exact-fallback construction. Each direct fold is protected by an outcome-disjoint opposite fold. A Clopper–Pearson confidence interval supplies both the variance lower bound and transport-bias upper bound required by Theorem S6.
- Claim boundary: the theorem is blockwise. Aggregate cross-fitted performance is measured empirically and is not presented as an unrestricted aggregate no-harm theorem.

The raw package is small: it uses five NHANES cycles and four feature files plus one very small HbA1c file per cycle. The expected total official download is on the order of tens of megabytes, not tens of gigabytes.

## Requirements

- MATLAB with Statistics and Machine Learning Toolbox.
- Internet access to `wwwn.cdc.gov` for automatic download, or manual placement of the official `.XPT` files.
- Do not independently download or inspect the three reserve `GHB` files before PREPARE is sealed and reviewed.

## Phase 1 — PREPARE only

1. Put this package in a new clean folder.
2. Open `RUN_PREPARE.m` in MATLAB.
3. Set `projectRoot` if desired.
4. Run the script once.

PREPARE downloads:

- `DEMO`, `BMX`, `BPQ` and `SMQ` for all five cycles;
- `GHB_G` for the source cycle;
- `GHB_H` for the transparent historical cycle.

PREPARE explicitly refuses to download or tolerate local copies of `GHB_I`, `GHB_J` or `GHB_L`. It freezes the source model, target scores, configuration and pre-outcome seal, then stops.

Send back:

- the complete MATLAB console output;
- `01_PreOutcome_Seal/StageU8_PreOutcome_Seal_v1_0.json`;
- `04_Logs/StageU8_PREPARE_COMPLETE_v1_0.txt`.

Do **not** create the authorization file yourself and do **not** run `RUN_UNSEAL.m` yet.

## Phase 2 — one-time UNSEAL

After the seal and hashes are checked, a real `StageU8_EXECUTION_AUTHORIZATION_v1_0.json` will be issued. Put it in `01_PreOutcome_Seal`, then run `RUN_UNSEAL.m` exactly once.

UNSEAL verifies every frozen hash before downloading the three reserve HbA1c files. It then writes:

- reserve truth and target summaries;
- 2,400 deterministic natural-prevalence witness replicates;
- cycle–budget state results;
- the frozen gate table and decision;
- a report and U8 figure;
- a durable manifest, completion record and canonical ZIP.

After all three reserve outcome files have been acquired, UNSEAL writes a permanent one-shot analysis-start marker immediately before reading any reserve outcome. If any error occurs after that marker is written, retain the full folder and console log. The code will refuse another analysis attempt; do not delete outputs or rerun as if the first execution did not happen.

## Automatic-download fallback

If `websave` is blocked, the pipeline writes a `MANUAL_DOWNLOAD_REQUIRED_*.txt` file with the exact official URL and exact destination. Download only that official file, leave it unchanged, place it at the stated destination and rerun the same phase. This is an acquisition repair, not permission to substitute a mirror.
