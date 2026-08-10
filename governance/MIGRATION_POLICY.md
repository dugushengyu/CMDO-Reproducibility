# CMDO code and storage migration policy

1. Drive is read-only during migration. No canonical record is deleted or overwritten.
2. U0–U7 originals are retained with Drive IDs and both Drive-byte and repository-normalized hashes.
3. A MATLAB port may replace a legacy implementation only after a documented golden-output comparison passes at the agreed tolerance.
4. Pre-outcome seals, authorizations and one-time reserve access remain binding after migration.
5. `RUN_ALL_CMDO` never invokes U9 `UNSEAL` implicitly.
6. Raw data, canonical ZIPs, model weights and generated results are local/external-storage assets, not ordinary Git objects.
7. Drive cleanup begins only after a complete local run, manifest verification and two independent recoverable copies.
