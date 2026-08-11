# T2-J historical dermoscopy reference-fingerprint bootstrap

Stage T2-J historically achieved complete reference-fingerprint coverage (1.0) before MILK10K cross-roster deduplication. The authoritative notebook reconstructs that cache by HTTP-fetching the frozen Stage 8 `source_locator` URLs. On 11 August 2026, the same frozen URLs yielded only 0.7042967707499332 coverage, which triggered the preregistered `MIN_REFERENCE_COVERAGE = 0.95` hold and removed MILK10K from the split-ready roster.

The historical Drive authority retains the exact Stage T2-J cache:

- `StageT2-J_Existing_Dermoscopy_Reference_Fingerprints_v0.1.csv`
- size: 6110670 bytes
- SHA-256: `d0383dfce4db6b147c5f68aaf4a07bd44f62352dd5179ae6cd205b59b762e2bd`

The reviewer archival profile materializes this byte-verified, non-outcome derived cache before Stage T2-J. The authoritative T2-J notebook is not modified: it detects the existing cache and uses its original code path. No label, endpoint, deduplication threshold, split rule, source axis, performance estimate, or scientific gate is changed.

This repair removes later third-party URL availability from a retrospective replay. It does not convert the archival continuation into a fresh prospective reproduction.

The runner also pins child-process text decoding to UTF-8 and makes console echo non-fatal on legacy Windows code pages. This affects logging only.
