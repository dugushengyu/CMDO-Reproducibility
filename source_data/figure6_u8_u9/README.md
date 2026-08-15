# Figure 6 source data

This directory contains the share-safe tabular source data for the final manuscript Figure 6, **Operational confirmation and the external boundary of guarded evidence reuse**.

- `U8_state.csv`, `U8_cycles.csv`, `U8_gates.csv`: completed U8 natural-prevalence NHANES temporal reserve.
- `U9A_targets.csv`, `U9A_states.csv`, `U9A_summary.json`: open multicentre UCI bridge/falsification branch.
- `U9B_states.csv`, `U9B_summary.json`: primary PhysioNet Challenge 2019 System-A-to-System-B external reserve.

No raw U9 patient-level PhysioNet PSV files are redistributed. U9 replicate-level witnesses are retained in the share-safe forensic export supplied with the submission; this repository snapshot carries the state/summary data required to regenerate Figure 6.

Interpretation boundary: the confidence-event certificate is blockwise. Aggregate cross-fitted MAE/MSE remains an empirical quantity and is not claimed to be universally non-increasing.
