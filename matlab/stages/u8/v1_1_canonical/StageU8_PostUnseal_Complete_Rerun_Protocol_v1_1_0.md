# Stage U8 disclosed post-unseal complete reconstruction protocol v1.1.0

Status: **authorized deterministic reconstruction after reserve-outcome access; not a new outcome-blind reserve experiment**.

## Why this complete package exists

The reviewed v1.0.1 `UNSEAL` execution validated the original pre-outcome seal and authorization, downloaded the three prespecified NHANES reserve HbA1c files, wrote the outcome-access and analysis-start records, reconstructed reserve truth, and computed all 2,400 frozen witness replicates in memory. It then stopped before aggregate output because MATLAB represented two cycle identifier columns as cell arrays and the original line compared them with `==`.

No model, threshold, cohort, target score, outcome definition, audit budget, random seed, fold, estimator, confidence interval, transport cap, gate, or decision rule caused the error or is changed here.

## Evidence retained

The package contains immutable copies of:

- the reviewed v1.0 pre-outcome seal;
- the original v1.0.1 code and v1.0 protocol;
- the original execution authorization and PREPARE completion log;
- the v1.0.2 recovery code, protocol, authorization, and analytical-core diff.

Their reviewed hashes are checked before any data operation.

## Complete reconstruction sequence

The single entry script creates a new work directory and:

1. downloads the same official feature files for all five NHANES cycles and HbA1c files for the 2011–2012 source and 2013–2014 transparent development cycles;
2. refits the prespecified source model and regenerates historical evidence and all 19,097 reserve score rows;
3. requires the reproduced historical-evidence and target-score file hashes, target-score row count, historical accuracy, historical AUC, threshold, official URLs, and every pre-outcome official input hash to match the reviewed seal;
4. writes a disclosed frozen-asset reproduction checkpoint;
5. downloads the already-disclosed official HbA1c files for the three reserve cycles;
6. reconstructs the unchanged reserve truth and the same 3 cycles × 4 budgets × 200 seeds = 2,400 witnesses;
7. writes all witness, state, target, gate, report, figure, manifest, and canonical records.

The serialized MATLAB model byte hash is recorded but is not a blocking identity condition because exact agreement of the regenerated target-score file is the downstream analytical identity condition. All downstream analysis uses that exactly reproduced frozen score file.

## Sole implementation correction

Immediately after the corresponding `struct2table` operations, the code performs:

```matlab
repTable.cycle = string(repTable.cycle);
targetTable.cycle = string(targetTable.cycle);
stateTable.cycle = string(stateTable.cycle);
```

These operations normalize non-analytical identifier containers only.

## Claim boundary

The final record must be described as a disclosed post-unseal deterministic reconstruction of the originally frozen U8 analysis. It must not be represented as a second independent reserve experiment or as an outcome-blind rerun. Theorem S6 remains blockwise; aggregate cross-fitted performance remains empirical. Legacy DDO-2 Stage 12 and its locked assets remain prohibited and unchanged.

