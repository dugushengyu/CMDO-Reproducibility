# T2-L runtime compatibility and replay-parent adapters

Stage T2-L v0.1 is retained byte-for-byte as the authoritative historical
source. The local reviewer runtime applies three non-destructive adapters.

## 1. LF-stable embedded companion materialisation

The authoritative pipeline materialises frozen theory, preregistration,
registry and manual-queue payloads with `Path.write_text`. Windows newline
translation changes the committed LF byte stream and therefore its SHA-256.

The adapted runtime writes the same UTF-8 payload bytes directly. The
authoritative embedded strings and their frozen commitments remain unchanged.

## 2. Targeted replay-parent rebinding

The historical T2-L source freezes T2-KR, T2-H and T3-PF parent self-hashes.
During archival continuation those stages are replayed and generate new,
self-consistent record hashes.

Only the three values inside T2-L's runtime `EXPECTED_PARENT` dictionary are
rebound to the verified replay-generated parent self-hashes. Historical hashes
embedded inside frozen preregistration or theory text are deliberately not
globally replaced.

This is a provenance/runtime continuation adapter, not a scientific change.

## 3. Windows DataLoader execution

T2-L executes at module top level while its PyTorch DataLoader historically
uses `num_workers=2`. Windows uses multiprocessing spawn, causing workers to
re-execute the complete top-level pipeline.

The runtime adapter therefore uses:

- Windows: `num_workers=0`
- non-Windows: `num_workers=2`

Dataset membership, deterministic ordering (`shuffle=False`), batch size,
image transforms, ResNet-50 IMAGENET1K_V2 weights, model state, embedding
normalisation, source axes, labels, seeds, budgets, estimators, thresholds,
gates and outcomes are unchanged.

## Verified replay

The Windows-adapted archival replay completed Stage T2-L with:

- 3 score-ready targets;
- 9 directed source-target edges;
- 35,280 multibudget result rows;
- 1 evidence-limited operational target;
- 2 evidence-demanding/right-censored targets;
- expanded LOTO Spearman 0.7068368086210209;
- single-pilot deployment remaining prohibited;
- locked-blind assets untouched;
- Stage 12 remaining false.

The stage decision remained the historical-governance-compatible partial
expansion decision rather than being upgraded by the adapter.
