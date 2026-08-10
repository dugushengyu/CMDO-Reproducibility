# Stage U2 — Run All and Dataset Acquisition Guide v0.1

## Authoritative notebook
CrossModal_StageU2_Mechanism_Multimetric_LabelEfficiency_External_NonBiomedical_v0.1_SELF_CONTAINED.ipynb

## Run
1. Open the notebook in Google Colab.
2. Select a GPU runtime.
3. Choose Runtime → Run all.
4. Keep Google Drive mounted and allow the notebook to finish.
5. Return the complete `STAGE U2 COMPLETE` banner, gate table, decision, and final SHA-256.

## What the notebook does
- Verifies the sealed Stage U0-U1 canonical parent and final record.
- Runs preregistered AUC finite-sample mechanism nulls across Gaussian, heavy-tailed, heteroscedastic, and mixture score families.
- Recomputes medical label-equivalence and sequential budget prediction.
- Automatically acquires CIFAR-10, CIFAR-10.1 v6, and selected CIFAR-10-C environments.
- Trains one frozen binary CIFAR model and evaluates AUC, AUPRC, balanced accuracy, Brier score, and log loss.
- Tests target-fixed-effect scaling, corruption-family holdout prediction, label-free transport, and frozen 0.6/0.4 fusion.
- Writes figures, ledgers, gates, complete JSON, canonical ZIP, and durable manifest to Drive.

## Dataset handling
No manual download is required for the primary U2 run.
- CIFAR-10 is acquired automatically through torchvision.
- CIFAR-10.1 v6 is acquired from the official repository, with a TensorFlow Datasets fallback.
- Selected CIFAR-10-C configurations are acquired through TensorFlow Datasets and cached persistently in Drive.
- The CIFAR-10-C source archive is large; do not interrupt the first acquisition merely because output pauses during download/extraction.
- Existing cached data are reused on later runs.

## Manual fallback only if automatic acquisition fails
The notebook records the failing URL/configuration. Only then use:
- CIFAR-10.1 official repository dataset files.
- CIFAR-10-C official Zenodo archive.
Do not manually download DomainNet for this stage.

## Governance
- DomainNet remains an untouched non-biomedical reserve.
- No new blind labels may be opened.
- The frozen transport/direct weights remain 0.6/0.4.
- Stage 12 remains prohibited.

