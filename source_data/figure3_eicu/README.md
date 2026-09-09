# Deferred sealed eICU multicentre replication — share-safe source data

This directory contains only aggregate/share-safe outputs from the completed one-shot eICU-CRD v2.0 reserve. It contains no raw patient-level eICU records and is the only eICU source used by the reviewer-facing Figure 3 renderer.

Scientific status:
- 20 independent reserve hospitals; screened-case budgets 64, 128 and 256; 200 deterministic replicates per hospital-budget state.
- Pooled direct MAE: 0.0277722933900823.
- Pooled CMDO MAE: 0.026762245 (rounded manuscript value 0.02676), relative improvement approximately 3.64%.
- Hospital breadth: 14/20 = 70%, below the prespecified 75% gate.
- Frozen verdict: `INTEGRITY_SUPPORTED_EMPIRICAL_SAFETY_NOT_CONFIRMED`.
- The deferred eICU result was executed after the 185-state U6-U9 post-completion synthesis was frozen and is not included in that 185-state pool or in its retrospective PCC projection.
- The eICU blockwise/covered-event certificate diagnostics are implementation diagnostics and are distinct from the manuscript's prospective composability certificate (PCC).

Immutable execution provenance:
- executed Amendment A1 code SHA-256: `5f72a5aba7650bc7ac51ac48c72db8e5d7ede19d856a75d29b8367387da43352`
- canonical shareable result ZIP SHA-256: `815bbc9a575a3e2eca5e227ad24d6d4f4e210eedac086f09287dac22c950b701`

Amendment A1 corrected only the official eICU field-name matching and Windows case-insensitive duplicate-path resolution before reserve outcomes were opened. It did not alter any scientific estimand, threshold, audit budget, seed, borrowing rule or gate.

The aggregate files in this directory are copied from the immutable canonical shareable execution record; the canonical ZIP itself is not rebuilt or modified by the submission freeze.
