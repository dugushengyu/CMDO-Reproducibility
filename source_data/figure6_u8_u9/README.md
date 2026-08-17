# U8/U9A/U9B source data for current Figure 5

This directory name is historical (`figure6_u8_u9`), but the records now serve as the independent audit companions for the current manuscript **Figure 5, Operational confirmation and the external admissibility boundary**.

- `U8_state.csv`, `U8_cycles.csv`, `U8_gates.csv`: completed U8 natural-prevalence NHANES temporal reserve.
- `U9A_targets.csv`, `U9A_states.csv`, `U9A_summary.json`: open multicentre UCI bridge/falsification branch.
- `U9B_states.csv`, `U9B_summary.json`: primary PhysioNet Challenge 2019 System-A-to-System-B external reserve.

The final `matlab/figures/main/Figure5.m` is a sealed single-file renderer: it embeds the frozen values needed to draw the figure and does not read these files at runtime. `scripts/audit_final_figure56.py` independently checks the embedded Figure 5 values against these tracked records.

No raw U9 patient-level PhysioNet PSV files are redistributed. U9 replicate-level witnesses are retained in the share-safe forensic export supplied with the submission; this repository carries the state/summary records required to audit the frozen manuscript figure.

Interpretation boundary: the confidence-event certificate is blockwise. Aggregate cross-fitted MAE/MSE remains an empirical quantity and is not claimed to be universally non-increasing.
