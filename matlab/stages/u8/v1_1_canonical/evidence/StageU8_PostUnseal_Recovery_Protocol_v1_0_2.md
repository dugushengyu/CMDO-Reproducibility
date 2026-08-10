# Stage U8 post-unseal recovery protocol v1.0.2

Status: **authorized implementation recovery after reserve access; not an outcome-blind first execution**.

## Incident fixed by this protocol

The reviewed v1.0.1 `UNSEAL` run validated the authorization and all frozen hashes, downloaded the three prespecified reserve HbA1c files, committed the permanent analysis-start record, reconstructed reserve truth, and computed all 2,400 frozen witness replicates in memory. It then stopped at original line 577 while aggregating cycle-level results:

`repTable.cycle == targetTable.cycle(i)`

Both cycle columns were MATLAB cell arrays, for which `==` is unsupported. The error was caused only by the container type of a non-analytical identifier.

After the failed call had left the debugger, the original main function was invoked once without arguments. Its default `PREPARE` branch found the existing seal and returned before any pipeline write. It did not overwrite the seal, reacquire outcomes, refit a model, rescore a target or execute the reserve analysis.

## Sole permitted correction

The recovery adds exactly these normalizations immediately after the corresponding `struct2table` operations:

```matlab
repTable.cycle = string(repTable.cycle);
targetTable.cycle = string(targetTable.cycle);
stateTable.cycle = string(stateTable.cycle);
```

This changes identifier containers only. It does not change a model, threshold, cohort, target score, outcome, historical estimate, audit budget, seed, replicate, fold, estimator, confidence interval, transport cap, gate or decision rule.

## Mandatory pre-execution validation

The recovery must refuse to run unless all of the following hold:

1. no completed U8 canonical record exists;
2. no earlier v1.0.2 recovery-start marker exists;
3. the reviewed pre-outcome seal hash is `5b6cab9bddd614b610a3acf5e69af0e1c304f14c4f38c55b62808be3835579cf`;
4. the untouched original v1.0.1 analysis code hash is `f963ff0b3d1ec692cc18c1954cee6b748c2b527a83a30b17aa20b9aef49898b2`;
5. the original protocol and execution-authorization hashes match their reviewed values;
6. every model, configuration, history and target-score hash matches the seal;
7. the original permanent analysis-start marker exists and matches the seal, original code, original authorization and outcome-access record;
8. the three local outcome files match the cycle, URL, path and first-access SHA-256 values recorded by the failed run;
9. the reserve-truth CSV written before the failure is value-equivalent to a fresh reconstruction from the unchanged target scores and already-accessed official outcome files;
10. a separately issued recovery authorization matches the recovery code and this protocol exactly.

No network download is permitted or performed by recovery v1.0.2.

## Deterministic reconstruction

After all validation passes, the recovery commits a permanent recovery-start marker and reconstructs the same prespecified analysis:

- 3 frozen reserve cycles;
- screened-case budgets `{128, 256, 512, 1024}`;
- 200 replicates per cycle and budget;
- frozen master seed `2026080902` and original deterministic derived-seed rule;
- 4 folds with opposite mapping `1↔3`, `2↔4`;
- original Clopper–Pearson intervals, transport weights, estimators, gates and decision hierarchy.

The witness count is therefore fixed at `3 × 4 × 200 = 2,400`. Recovery is a deterministic reconstruction of the analysis that failed during result aggregation. It is not described as a second independent reserve experiment or as an outcome-blind execution.

## Evidence and claim boundary

The final canonical record must retain:

- the original seal, execution authorization, original code and protocol;
- the original outcome-access record and analysis-start marker;
- the pre-failure reserve truth;
- this recovery protocol, recovery authorization and recovery code;
- a machine-readable implementation-deviation record and recovery-start marker;
- all witnesses, state summaries, gates, report, figures, manifest and canonical ZIP.

The scientific interpretation remains the frozen U8 interpretation. Theorem S6 is blockwise; aggregate cross-fitted performance remains empirical. Any manuscript or reviewer package using U8 must disclose the post-unseal implementation correction in its reproducibility or protocol-deviation record.

